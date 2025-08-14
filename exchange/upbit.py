import requests
from bs4 import BeautifulSoup
import json
import hashlib
import os
import re
import time
import random
import asyncio
import sys
from pprint import pprint
import traceback
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepseek_analyzer import DeepSeekAnalyzer

class UpbitScraper:
    def __init__(self, analyzer: DeepSeekAnalyzer):
        self.analyzer = analyzer
        self.base_url = "https://upbit.com"
        self.headers = {
            'accept': 'application/json',
            'accept-language': 'en-KR, en;q=1, en-US;q=0.1',
            'cache-control': 'no-cache',
            'origin': 'https://upbit.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://upbit.com/',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
    
    def get_announcements_id(self):
        params = {
            'os': 'web',
            'page': '1',
            'per_page': '20',
            'category': 'trade',
        }

        response = requests.get('https://api-manager.upbit.com/api/v1/announcements', params=params, headers=self.headers)
        print(response.text)
        return response.json()['data']['notices']
    
    def get_announcement_detail(self, announcement_id):
        url = f"https://api-manager.upbit.com/api/v1/announcements/{announcement_id}"
        response = requests.get(url, headers=self.headers)
        json_data = response.json()
        return {
            "text": json_data['data']['body']
        }
    
    def run_scraping(self):
        """运行爬虫主流程"""
        try:
            
            # 获取公告分类数据
            announcements = self.get_announcements_id()
            
            for i, article in enumerate(announcements):
                article_id = article.get('id')
                text_file_name = f'announcements_text/upbit_{article_id}.txt'
                json_file_name = f'announcements_json/upbit_{article_id}.json'
                if os.path.exists(text_file_name) and os.path.exists(json_file_name):
                    print(f"公告详情已存在: {text_file_name}")
                    continue
                print("=== 获取公告详情 ===")
                print(f"   标题: {article.get('title', 'N/A')}")
                print(f"   URL: https://upbit.com/service_center/notice?id={article_id}")
                detail_result = self.get_announcement_detail(article.get('id'))
                if detail_result:
                    print("\n=== 纯文字内容 ===")
                    text_content = detail_result['text']
                    print(text_content[:1000] + "..." if len(text_content) > 1000 else text_content)
                    
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
                        self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'upbit'})
                        
                    except Exception as e:
                        print(f"DeepSeek分析失败: {traceback.format_exc()}")
                else:
                    print("获取详情失败")
                    exit()
            
        except Exception as e:
            print(f"程序执行出错: {traceback.format_exc()}")
        

if __name__ == "__main__":
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = UpbitScraper(analyzer)
    scraper.run_scraping()