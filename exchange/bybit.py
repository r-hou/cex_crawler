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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepseek_analyzer import DeepSeekAnalyzer

class BybitScraper:
    def __init__(self, analyzer: DeepSeekAnalyzer):
        self.analyzer = analyzer
        self.exchange = ccxt.bybit()
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://announcements.bybit.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://announcements.bybit.com/en/?category=delistings&page=1',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'traceparent': '00-e644fcbc13aaf6c30f2300b60aefbafc-e908187fa171a8d5-01',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        }

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
        article_text = ''
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
            for i, announcement in enumerate(announcements):  # 只显示前3条
                print(f"   标题: {announcement.get('title', 'N/A')}")
                print(f"   URL: https://announcements.bybit.com/zh-MY/{announcement.get('url', '')}")
                
                # 获取公告详情
                article_id = hashlib.md5(announcement.get('url', '').encode('utf-8')).hexdigest()
                text_file_name = f'announcements_text/bybit_{article_id}.txt'
                json_file_name = f'announcements_json/bybit_{article_id}.json'
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
                        self.analyzer.save_analysis_result(analysis_result,    json_file_name, updates={'exchange': 'bybit'})
                        
                    except Exception as e:
                        print(f"DeepSeek分析失败: {traceback.format_exc()}")

                    
                else:
                    print("获取公告详情失败")
        except Exception as e:
            print(f"获取Bybit公告详情失败: {traceback.format_exc()}")

if __name__ == "__main__":
    scraper = BybitScraper()
    scraper.run_scraping()
