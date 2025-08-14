import requests
from bs4 import BeautifulSoup
import json
import pprint
import os
import sys
import traceback
import uuid


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepseek_analyzer import DeepSeekAnalyzer

class GateScraper:
    def __init__(self, analyzer: DeepSeekAnalyzer):
        self.analyzer = analyzer
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://www.gate.com/',
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
        
    def get_build_id(self):
        url = 'https://www.gate.com/zh/announcements/newfutureslistings'
        response = requests.get(url, headers=self.headers)
        json_data = self.extract_json_from_script(response.text)
        return json_data['buildId']
    
    def get_announcements_id(self):
        self.build_id = self.get_build_id()
        spot_url = f'https://www.gate.com/announcements/_next/data/{self.build_id}/zh/announcements/newspotlistings.json?category=newspotlistings'
        futures_url = f'https://www.gate.com/announcements/_next/data/{self.build_id}/zh/announcements/newfutureslistings.json?category=newfutureslistings'
        spot_response_json = requests.get(spot_url, headers=self.headers).json()
        futures_response_json = requests.get(futures_url, headers=self.headers).json()
        return spot_response_json["pageProps"]["listData"]["list"] + futures_response_json["pageProps"]["listData"]["list"]
    
    def get_announcement_detail(self, announcement_id):
        url = f'https://www.gate.com/announcements/_next/data/{self.build_id}/zh/announcements/article/{announcement_id}.json?slug={announcement_id}'
        response = requests.get(url, headers=self.headers)
        json_data = response.json()
        # with open('gate_announcement_detail.json', 'w') as f:
        #     json.dump(json_data, f, ensure_ascii=False, indent=4)
        text_content = json_data["pageProps"]["tdkTitle"] + "\n" + json_data["pageProps"]["detail"]["desc"]
        return text_content
    
    def run_scraping(self):
        try:
            announcements = self.get_announcements_id()
            print("\n=== 公告列表 ===")
            for i, announcement in enumerate(announcements):  # 只显示前3条
                article_id = announcement.get('id', uuid.uuid4())
                text_file_name = f'announcements_text/gate_{article_id}.txt'
                json_file_name = f'announcements_json/gate_{article_id}.json'
                if os.path.exists(text_file_name) and os.path.exists(json_file_name):
                    print(f"公告详情已存在: {text_file_name}")
                    continue
                print(f"   标题: {announcement.get('title', 'N/A')}")
                print(f"   URL: https://www.gate.com/zh/announcements/article/{announcement.get('id', '')}")
                
                # 获取公告详情
                text_content = self.get_announcement_detail(announcement.get('id', ''))
                if text_content:
                    print("\n=== 提取的文字数据 ===")
                    pprint.pprint(text_content, indent=4)
                    with open(text_file_name, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    print(f"\nTEXT数据已保存到: {text_file_name}")
                    # 使用OpenAI分析内容
                    print("\n=== 使用DeepSeek分析公告内容 ===")
                    try:
                        # analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
                        analysis_result = self.analyzer.analyze_announcement(text_content)
                        
                        # 显示分析结果
                        self.analyzer.print_analysis_result(analysis_result)
                        
                        # 保存分析结果
                        self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'gate'})
                        
                    except Exception as e:
                        print(f"DeepSeek分析失败: {traceback.format_exc()}")

                    
                else:
                    print("获取公告详情失败")
        except Exception as e:
            print(f"获取Bybit公告详情失败: {traceback.format_exc()}")


if __name__ == "__main__":
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = GateScraper(analyzer)
    scraper.run_scraping()