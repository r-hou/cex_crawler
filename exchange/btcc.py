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

from deepseek_analyzer import DeepSeekAnalyzer
from .base_scraper import BaseScraper
import pandas as pd

class BtccScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10, offset_days: int = 7, analyzer_api_key= None):
        super().__init__("btcc", "https://www.btcc.com", analyzer, debug, max_size, offset_days, analyzer_api_key)
        

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
                
    def get_announcement_detail(self, announcement_id):
        url = f'https://www.btcc.com/en-US/detail/{announcement_id}'
        response = requests.get(url, headers=self.headers)
        text = self.parse_announcement_content(response.text)
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
    
    async def run_scraping(self):
        announcements = self.get_announcements_id()
        
        # Counter for processed announcements in debug mode
        processed_count = 0
        
        for i, announcement in enumerate(announcements):
            # 获取公告详情
            article_id = announcement.get('id', uuid.uuid4())
            # text_file_name = os.path.join(self.output_dir, f"btcc_{article_id}.txt")
            json_file_name = os.path.join(self.output_dir, f"btcc_{article_id}.json")
            release_time = announcement.get('ctime')
            release_time_str = pd.to_datetime(release_time, unit='ms', utc=True).tz_convert('Asia/Hong_Kong').strftime('%Y-%m-%d %H:%M:%S')
            if release_time_str < (pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)).strftime('%Y-%m-%d %H:%M:%S'):
                print(f"公告 {announcement.get('title', 'N/A')} 发布时间 {release_time_str} 小于 {pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)}，跳过")
                with open(json_file_name, 'w', encoding='utf-8') as f:
                    json.dump({'release_time': release_time_str, 'text': "", 'url': f"https://www.btcc.com/en-US/detail/{announcement.get('id', '')}", 'title': announcement.get('title', 'N/A'),"exchange": "btcc"}, f, ensure_ascii=False, indent=4)
                continue
            
            if os.path.exists(json_file_name):
                print(f"公告详情已存在: {json_file_name}")
                continue
            print(f"   标题: {announcement.get('title', 'N/A')}")
            print(f"   URL: https://www.btcc.com/en-US/detail/{announcement.get('id', '')}")
            text_content = self.get_announcement_detail(announcement.get('id', ''))
            if text_content:
                print("\n=== 提取的文字数据 ===")
                pprint.pprint(text_content, indent=4)
                # 保存到文件
                # with open(text_file_name, 'w', encoding='utf-8') as f:
                #     f.write(text_content)
                # print(f"\n纯文字内容已保存到: {text_file_name}")
                # 使用OpenAI分析内容
                print("\n=== 使用DeepSeek分析公告内容 ===")
                try:
                    # analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
                    analysis_result = self.analyzer.analyze_announcement(text_content)
                    
                    # 显示分析结果
                    self.analyzer.print_analysis_result(analysis_result)
                    
                    # 保存分析结果
                    self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'btcc',
                        'title': announcement.get('title', 'N/A'),
                        'url': f"https://www.btcc.com/en-US/detail/{announcement.get('id', '')}",
                        'release_time': release_time_str,
                        'content': text_content
                    })

                    

                    # Increment counter for successfully processed announcements
                    processed_count += 1
                    # if self.debug and processed_count >= self.max_size:
                    #     print(f"Debug mode: Reached max_size limit ({self.max_size}), stopping...")
                    #     break
                    
                except Exception as e:
                    print(f"DeepSeek分析失败: {traceback.format_exc()}")

                
            else:
                print("获取公告详情失败")
            
            # Break outer loop if we've reached max_size in debug mode
            if self.debug and processed_count >= self.max_size:
                break



if __name__ == "__main__":
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = BtccScraper(analyzer, debug=True, max_size=3)
    scraper.run_scraping()