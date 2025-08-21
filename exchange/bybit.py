import pandas as pd
import ccxt
import time
import pprint
import json
import requests
from bs4 import BeautifulSoup
import re
import traceback
import uuid
import os
import sys
import hashlib
from deepseek_analyzer import DeepSeekAnalyzer
from .base_scraper import BaseScraper

class BybitScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10):
        super().__init__("bybit", "https://www.bybit.com", analyzer, debug, max_size)
        

    def get_announcements_id(self):

        delisting_json_data = {
            'data': {
                'query': '',
                'page': 0,
                'hitsPerPage': 8,
                'filters': "category.key: 'delistings'",
            },
        }

        listing_json_data = {
            'data': {
                'query': '',
                'page': 0,
                'hitsPerPage': 20,
                'filters': "category.key: 'new_crypto'",
            },
        }
        url = 'https://announcements.bybit.com/x-api/announcements/api/search/v1/index/announcement-posts_zh-my'
        delisting_response = requests.post(
            url,
            headers=self.headers,
            json=delisting_json_data,
        )
        listing_response = requests.post(
            url,
            headers=self.headers,
            json=listing_json_data,
        )
        return delisting_response.json()['result']['hits']+listing_response.json()['result']['hits']
    
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
        

    def get_announcement_detail(self, announcement_url):
        url = f'https://announcements.bybit.com/zh-MY/{announcement_url}'
        print(url)
        response = requests.get(url, headers=self.headers)
        html_content = response.text
        
        # 提取script标签中的JSON数据
        json_data = self.extract_json_from_script(html_content)
        article_elements = json_data['props']['pageProps']['articleDetail']['content']['json']['children']
        article_text = json_data['props']['pageProps']['articleDetail'].get('description', '')
        article_text += "公共发布日期:"+json_data['props']['pageProps']['articleDetail'].get('date', '')+"\n"
        for element in article_elements:
            if element['type'] == 'p':
                article_text += element['children'][0]['text'].replace('\'', '')
            # if element['type'] == 'h2':
            #     print(element['children'][0]['text'])
            #     break
            # if element['type'] == 'h3':
            #     print(element['children'][0]['text'])
            #     break
        return article_text
    
    
    
    def run_scraping(self):
        try:
            announcements = self.get_announcements_id()
            print("\n=== 公告列表 ===")
            
            # Counter for processed announcements in debug mode
            processed_count = 0
            
            for i, announcement in enumerate(announcements):
                print(f"   标题: {announcement.get('title', 'N/A')}")
                print(f"   URL: https://announcements.bybit.com/zh-MY/{announcement.get('url', '')}")
                
                # 获取公告详情
                article_id = hashlib.md5(announcement.get('url', '').encode('utf-8')).hexdigest()
                text_file_name = os.path.join(self.output_dir, f"bybit_{article_id}.txt")
                json_file_name = os.path.join(self.output_dir, f"bybit_{article_id}.json")
                if os.path.exists(text_file_name) and os.path.exists(json_file_name):
                    print(f"公告详情已存在: {text_file_name}")
                    continue
                text_content = self.get_announcement_detail(announcement.get('url', ''))
                if text_content:
                    print("\n=== 提取的文字数据 ===")
                    pprint.pprint(text_content, indent=4)
                    # 保存JSON数据
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
                        self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'bybit'})
                        
                        # Increment counter for successfully processed announcements
                        processed_count += 1
                        if self.debug and processed_count >= self.max_size:
                            print(f"Debug mode: Reached max_size limit ({self.max_size}), stopping...")
                            break
                        
                    except Exception as e:
                        print(f"DeepSeek分析失败: {traceback.format_exc()}")

                    
                else:
                    print("获取公告详情失败")
                
                # Break outer loop if we've reached max_size in debug mode
                if self.debug and processed_count >= self.max_size:
                    break
        except Exception as e:
            print(f"获取Bybit公告详情失败: {traceback.format_exc()}")

if __name__ == "__main__":
    scraper = BybitScraper()
    scraper.run_scraping()
