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
import pandas as pd

from deepseek_analyzer import DeepSeekAnalyzer
from .base_scraper import BaseScraper

class LbankScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10, offset_days: int = 7, analyzer_api_key= None):
        super().__init__("lbank", "https://www.lbank.com", analyzer, debug, max_size, offset_days, analyzer_api_key)
        

    def get_session_id(self):
        # url = 'https://www.lbank.com/support/announcement'
        url = "https://www.lbank.com/support/sections/latest-news/notice"
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
        print(all_links)
        for link in all_links:
            link_text = link.get_text(strip=True)
            href = link.get('href')
            
            # 检查是否包含目标文字
            for target_text in target_texts:
                if target_text in link_text.lower():
                    print(link_text)
                    target_links.append({
                        'text': link_text,
                        'href': href,
                        'full_url': f"https://www.lbank.com{href}" if href and href.startswith('/') else href
                    })
                    print(f"找到目标链接: {link_text} -> {href}")
                    break  # 避免重复添加同一个链接
        print(target_links)
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

    async def run_scraping(self):
        announcements = self.get_announcements_id()
        # print(len(announcements))
        self.build_id = self.get_build_id()
        
        # Counter for processed announcements in debug mode
        processed_count = 0
        
        for i, announcement in enumerate(announcements):
            article_id = announcement.get('code', uuid.uuid4())
            json_file_name = os.path.join(self.output_dir, f"lbank_{article_id}.json")
            release_time = int(announcement.get('contentShowTime'))
            release_time_str = pd.to_datetime(release_time, unit='ms', utc=True).tz_convert('Asia/Hong_Kong').strftime('%Y-%m-%d %H:%M:%S')
            if release_time_str < (pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)).strftime('%Y-%m-%d %H:%M:%S'):
                print(f"公告 {announcement.get('title', 'N/A')} 发布时间 {release_time_str} 小于 {pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)}，跳过")
                with open(json_file_name, 'w', encoding='utf-8') as f:
                    json.dump({'release_time': release_time_str, 'text': "", 'url': f"https://www.lbank.com/support/articles/{announcement.get('code', '')}", 'title': announcement.get('title', 'N/A'),"exchange": "lbank"}, f, ensure_ascii=False, indent=4)
                continue
            # text_file_name = os.path.join(self.output_dir, f"lbank_{article_id}.txt")
            
            if os.path.exists(json_file_name):
                print(f"公告详情已存在: {json_file_name}")
                continue
            print(f"   标题: {announcement.get('title', 'N/A')}")
            print(f"   URL: https://www.lbank.com/support/articles/{announcement.get('code', '')}")
            
            # 获取公告详情
            text_content = self.get_announcement_detail(announcement.get('code', ''))
            if text_content:
                print("\n=== 提取的文字数据 ===")
                pprint.pprint(text_content, indent=4)
                # with open(text_file_name, 'w', encoding='utf-8') as f:
                #     f.write(text_content)
                # print(f"\nTEXT数据已保存到: {text_file_name}")
                # 使用OpenAI分析内容
                print("\n=== 使用DeepSeek分析公告内容 ===")
                try:
                    # analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
                    analysis_result = self.analyzer.analyze_announcement(text_content)
                    
                    # 显示分析结果
                    self.analyzer.print_analysis_result(analysis_result)
                    
                    # 保存分析结果
                    self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'lbank',
                        'title': announcement.get('title', 'N/A'),
                        'url': f"https://www.lbank.com/support/articles/{announcement.get('code', '')}",
                        'release_time': release_time_str,
                        'content': text_content
                    })

                    
                    # Increment counter for successfully processed announcements
                    processed_count += 1
                    if self.debug and processed_count >= self.max_size:
                        print(f"Debug mode: Reached max_size limit ({self.max_size}), stopping...")
                        break
                    
                except Exception as e:
                    print(f"DeepSeek分析失败: {traceback.format_exc()}")

                
            else:
                print("获取公告详情失败")
            
            # # Break outer loop if we've reached max_size in debug mode
            # if self.debug and processed_count >= self.max_size:
            #     break

if __name__ == "__main__":
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = LbankScraper(analyzer, debug=True, max_size=3)
    scraper.run_scraping()