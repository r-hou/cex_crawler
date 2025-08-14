import requests
from bs4 import BeautifulSoup
import json
import pprint
import os
import sys
import traceback
import uuid
import re
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepseek_analyzer import DeepSeekAnalyzer


class BtccScraper:
    def __init__(self, analyzer: DeepSeekAnalyzer):
        self.analyzer = analyzer
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://www.lbank.com/',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        }

    def extract_json_from_script(self, html_content):
        """从HTML的script标签中提取JSON数据"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            json_data = {}
            
            # 1. 优先查找Next.js的__NEXT_DATA__ script标签
            next_data_script = soup.find('script', {'id': '__NEXT_DATA__', 'type': 'application/json'})
            if next_data_script and next_data_script.string:
                try:
                    json_data = json.loads(next_data_script.string.strip())
                    print("成功提取 __NEXT_DATA__ 数据")
                except json.JSONDecodeError as e:
                    print(f"解析 __NEXT_DATA__ JSON失败: {e}")
            
            
            if not json_data:
                print("未找到script标签中的JSON数据")
            
            return json_data
            
        except Exception as e:
            print(f"提取script标签JSON数据失败: {e}")
            return {}
    def extract_text_from_html(self, html_content):
        """从HTML内容中提取纯文字"""
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除script和style标签
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # 获取纯文字
            text = soup.get_text()
            
            # 清理文字（移除多余空白字符）
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # 移除特殊字符和多余的换行
            text = re.sub(r'\n+', '\n', text)
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()
            
        except Exception as e:
            print(f"文字提取失败: {e}")
            # 如果BeautifulSoup失败，使用简单的正则表达式
            try:
                # 移除HTML标签
                text = re.sub(r'<[^>]+>', '', html_content)
                # 移除多余空白
                text = re.sub(r'\s+', ' ', text)
                return text.strip()
            except:
                return html_content
            
    def get_announcement_detail(self, announcement_id):
        url = f'https://www.btcc.com/en-US/detail/{announcement_id}'
        response = requests.get(url, headers=self.headers)
        text = self.extract_text_from_html(response.text)
        return text
    
    def get_announcements_id(self):
        url = 'https://www.btcc.com/en-US/announcements'
        response = requests.get(url, headers=self.headers)
        json_data = self.extract_json_from_script(response.text)
        # with open('btcc_announcements.json', 'w') as f:
        #     json.dump(json_data, f, ensure_ascii=False, indent=4)
        # pprint.pprint(json_data['props']['pageProps']['list'])
        return json_data['props']['pageProps']['list']
        # soup = BeautifulSoup(response.text, 'html.parser')
        # announcements = soup.find_all('a', class_='announcement-item')
        # return announcements
    
    def run_scraping(self):
        announcements = self.get_announcements_id()
        for i, announcement in enumerate(announcements):  # 只显示前3条
            # 获取公告详情
            article_id = announcement.get('id', uuid.uuid4())
            text_file_name = f'announcements_text/btcc_{article_id}.txt'
            json_file_name = f'announcements_json/btcc_{article_id}.json'
            if os.path.exists(text_file_name) and os.path.exists(json_file_name):
                print(f"公告详情已存在: {text_file_name}")
                continue
            print(f"   标题: {announcement.get('title', 'N/A')}")
            print(f"   URL: https://www.btcc.com/en-US/detail/{announcement.get('id', '')}")
            text_content = self.get_announcement_detail(announcement.get('id', ''))
            if text_content:
                print("\n=== 提取的文字数据 ===")
                pprint.pprint(text_content, indent=4)
                # 保存到文件
                with open(text_file_name, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                print(f"\n纯文字内容已保存到: {text_file_name}")
                # 使用OpenAI分析内容
                print("\n=== 使用DeepSeek分析公告内容 ===")
                try:
                    # analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
                    analysis_result = self.analyzer.analyze_announcement(text_content)
                    
                    # 显示分析结果
                    self.analyzer.print_analysis_result(analysis_result)
                    
                    # 保存分析结果
                    self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'btcc'})
                    
                except Exception as e:
                    print(f"DeepSeek分析失败: {traceback.format_exc()}")

                
            else:
                print("获取公告详情失败")



if __name__ == "__main__":
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = BtccScraper(analyzer)
    scraper.run_scraping()