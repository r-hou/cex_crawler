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
import pandas as pd
from deepseek_analyzer import DeepSeekAnalyzer
from .base_scraper import BaseScraper


class UpbitScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10, offset_days: int = 7, analyzer_api_key= None):
        super().__init__("upbit", "https://upbit.com", analyzer, debug, max_size, offset_days, analyzer_api_key)
        

    def get_announcements_id(self):
        params = {
            'os': 'web',
            'page': '1',
            'per_page': '20',
            'category': 'trade',
        }

        response = requests.get('https://api-manager.upbit.com/api/v1/announcements', params=params, headers=self.headers)
        return response.json()['data']['notices']
    
    def get_announcement_detail(self, announcement_id):
        url = f"https://api-manager.upbit.com/api/v1/announcements/{announcement_id}"
        response = requests.get(url, headers=self.headers)
        json_data = response.json()
        return {
            "text": json_data['data']['body']
        }
    
    async def run_scraping(self):
        """运行爬虫主流程"""
        try:
            
            # 获取公告分类数据
            announcements = self.get_announcements_id()
            
            for i, article in enumerate(announcements):
                article_id = article.get('id')
                url = f"https://upbit.com/service_center/notice?id={article_id}"
                json_file_name = os.path.join(self.output_dir, f"upbit_{article_id}.json")
                release_time = article.get('first_listed_at')
                release_time_str = pd.to_datetime(release_time).tz_convert('Asia/Hong_Kong').strftime('%Y-%m-%d %H:%M:%S')
                if release_time_str < (pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)).strftime('%Y-%m-%d %H:%M:%S'):
                    print(f"公告 {article.get('title', 'N/A')} 发布时间 {release_time_str} 小于 {pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)}，跳过")
                    with open(json_file_name, 'w', encoding='utf-8') as f:
                        json.dump({'release_time': release_time_str, 'text': "", 'url': url, 'title': article.get('title', 'N/A'),"exchange": "upbit"}, f, ensure_ascii=False, indent=4)
                    continue
                # text_file_name = os.path.join(self.output_dir, f"upbit_{article_id}.txt")
                
                if os.path.exists(json_file_name):
                    print(f"公告详情已存在: {json_file_name}")
                    continue
                print("=== 获取公告详情 ===")
                print(f"   标题: {article.get('title', 'N/A')}")
                print(f"   URL: {url}")
                detail_result = self.get_announcement_detail(article.get('id'))
                if detail_result:
                    print("\n=== 纯文字内容 ===")
                    text_content = detail_result['text']
                    print(text_content[:1000] + "..." if len(text_content) > 1000 else text_content)
                    
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
                        self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'upbit',
                            'title': article.get('title', 'N/A'),
                            'url': url,
                            'release_time': release_time_str,
                            'content': text_content
                        })
                        processed_count += 1

                        # if self.debug and processed_count >= self.max_size:
                        #     print(f"Debug mode: Reached max_size limit ({self.max_size}), stopping...")
                        #     break
                        
                    except Exception as e:
                        print(f"DeepSeek分析失败: {traceback.format_exc()}")
                else:
                    print("获取详情失败")

            
        except Exception as e:
            print(f"程序执行出错: {traceback.format_exc()}")
        

if __name__ == "__main__":
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = UpbitScraper(analyzer, debug=True, max_size=3)
    scraper.run_scraping()