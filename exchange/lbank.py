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


class LbankScraper:
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
        self.build_id = self.get_build_id()

    def get_session_id(self):
        url = 'https://www.lbank.com/support/announcement'
        response = requests.get(url, headers=self.headers)
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有a标签
        all_links = soup.find_all('a')
        
        # 查找文字是"New Listing"和"System Notification"的a标签
        target_links = []
        
        # 定义目标文字的各种可能变体
        target_texts = [
            'New Listing', 'new listing', 'NEW LISTING',
            'System Notification', 'system notification', 'SYSTEM NOTIFICATION'
        ]
        
        for link in all_links:
            link_text = link.get_text(strip=True)
            href = link.get('href')
            
            # 检查是否包含目标文字
            for target_text in target_texts:
                if target_text in link_text:
                    target_links.append({
                        'text': link_text,
                        'href': href,
                        'full_url': f"https://www.lbank.com{href}" if href and href.startswith('/') else href
                    })
                    print(f"找到目标链接: {link_text} -> {href}")
                    break  # 避免重复添加同一个链接
        
        # 如果没有找到，尝试其他方法
        if not target_links:
            print("未找到目标链接，尝试其他方法...")
            
            # 方法1: 查找包含特定class的链接
            class_links = soup.find_all('a', class_=lambda x: x and ('listing' in x.lower() or 'notification' in x.lower()))
            for link in class_links:
                link_text = link.get_text(strip=True)
                href = link.get('href')
                target_links.append({
                    'text': link_text,
                    'href': href,
                    'full_url': f"https://www.lbank.com{href}" if href and href.startswith('/') else href
                })
                print(f"通过class找到链接: {link_text} -> {href}")
            
            # 方法2: 查找包含特定id的链接
            id_links = soup.find_all('a', id=lambda x: x and ('listing' in x.lower() or 'notification' in x.lower()))
            for link in id_links:
                link_text = link.get_text(strip=True)
                href = link.get('href')
                target_links.append({
                    'text': link_text,
                    'href': href,
                    'full_url': f"https://www.lbank.com{href}" if href and href.startswith('/') else href
                })
                print(f"通过id找到链接: {link_text} -> {href}")
            
            # 方法3: 查找包含特定data属性的链接
            data_links = soup.find_all('a', attrs={'data-*': lambda x: x and ('listing' in str(x).lower() or 'notification' in str(x).lower())})
            for link in data_links:
                link_text = link.get_text(strip=True)
                href = link.get('href')
                target_links.append({
                    'text': link_text,
                    'href': href,
                    'full_url': f"https://www.lbank.com{href}" if href and href.startswith('/') else href
                })
                print(f"通过data属性找到链接: {link_text} -> {href}")
            
            # 方法4: 查找所有链接并打印，帮助调试
            if not target_links:
                print("打印所有链接以便调试:")
                for i, link in enumerate(all_links[:20]):  # 只打印前20个
                    link_text = link.get_text(strip=True)
                    href = link.get('href')
                    if link_text and href:
                        print(f"{i+1}. {link_text} -> {href}")
        
        return target_links
    

    def get_listing_announcements_id(self, target_link):
        json_data = {
                'pageNo': 1,
                'pageSize': 15,
                'topCategory': 'NOTICE',
                'categoryCode': target_link.split('/')[-1],
            }

        response = requests.post(
            'https://ccapi.rerrkvifj.com/huamao-media-center/notice/category/noticeList',
            headers=self.headers,
            json=json_data,
        )
        return response.json()['data']['resultList']
    
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
        url = 'https://www.lbank.com/support/sections/latest-news/notice'
        response = requests.get(url, headers=self.headers)
        json_data = self.extract_json_from_script(response.text)
        return json_data['buildId']
    
    
    def get_announcement_detail(self, announcement_id):
        url = f'https://www.lbank.com/_next/data/{self.build_id}/en-US/support/articles/{announcement_id}.json?slug={announcement_id}'
        response = requests.get(url, headers=self.headers)
        title = response.json()['pageProps']['detail']["noticeContent"]["title"]
        content = response.json()['pageProps']['detail']['noticeContent']['summary']
        return title + "\n" + content
    
    def get_announcements_id(self):
        # 获取目标链接
        target_links = self.get_session_id()
        all_announcements = []
        for link in target_links:
            json_data = {
                'pageNo': 1,
                'pageSize': 15,
                'topCategory': 'NOTICE',
                'categoryCode': link['href'].split('/')[-1],
            }

            response = requests.post(
                'https://ccapi.rerrkvifj.com/huamao-media-center/notice/category/noticeList',
                headers=self.headers,
                json=json_data,
            )
            if ("Listing" in link['text']) or ("listing" in link['text']):
                all_announcements += response.json()['data']['resultList']
            elif ("Notification" in link['text']) or ("notification" in link['text']):
                res = response.json()['data']['resultList']
                delisting_announcements = [i for i in res if ('Delist' in i['title']) or ('delist' in i['title'])]
                all_announcements += delisting_announcements

        return all_announcements

    def run_scraping(self):
        announcements = self.get_announcements_id()
        self.build_id = self.get_build_id()
        for i, announcement in enumerate(announcements):  # 只显示前3条
            article_id = announcement.get('code', uuid.uuid4())
            text_file_name = f'announcements_text/lbank_{article_id}.txt'
            json_file_name = f'announcements_json/lbank_{article_id}.json'
            if os.path.exists(text_file_name) and os.path.exists(json_file_name):
                print(f"公告详情已存在: {text_file_name}")
                continue
            print(f"   标题: {announcement.get('title', 'N/A')}")
            print(f"   URL: https://www.lbank.com/support/articles/{announcement.get('code', '')}")
            
            # 获取公告详情
            text_content = self.get_announcement_detail(announcement.get('code', ''))
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
                    self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'lbank'})
                    
                except Exception as e:
                    print(f"DeepSeek分析失败: {traceback.format_exc()}")

                
            else:
                print("获取公告详情失败")

if __name__ == "__main__":
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = LbankScraper(analyzer)
    scraper.run_scraping()