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

class OkxScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10, offset_days: int = 7, analyzer_api_key= None):
        super().__init__("okx", "https://www.okx.com", analyzer, debug, max_size, offset_days, analyzer_api_key)
    
    async def get_page_content(self, url, state='load'):
        """获取页面内容"""
        await self.page.goto(url)
        await self.random_delay(2, 4)
        await self.page.wait_for_load_state(state)
        return await self.page.content()

    async def get_announcements_id(self):
        listing_url = "https://www.okx.com/zh-hans/help/section/announcements-new-listings"
        delisting_url = "https://www.okx.com/zh-hans/help/section/announcements-delistings"
        listing_content = await self.get_page_content(listing_url)
        delisting_content = await self.get_page_content(delisting_url)

        listing_json_data = self.extract_json_from_script(listing_content)
        delisting_json_data = self.extract_json_from_script(delisting_content)

        res = listing_json_data['appContext']['initialProps']["sectionData"]["articleList"]["items"]+delisting_json_data['appContext']['initialProps']["sectionData"]["articleList"]["items"]
        return res
    
    def extract_json_from_script(self, html_content):
        """从HTML的script标签中提取JSON数据"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            json_data = {}
            
            # 1. 优先查找Next.js的__NEXT_DATA__ script标签
            next_data_script = soup.find('script', {'data-id': '__app_data_for_ssr__', 'type': 'application/json'})
            if next_data_script and next_data_script.string:
                try:
                    json_data = json.loads(next_data_script.string.strip())
                    print("成功提取 __app_data_for_ssr__ 数据")
                except json.JSONDecodeError as e:
                    print(f"解析 __app_data_for_ssr__ JSON失败: {traceback.format_exc()}")
            
            
            if not json_data:
                print("未找到script标签中的JSON数据")
            
            return json_data
            
        except Exception as e:
            print(f"提取script标签JSON数据失败: {traceback.format_exc()}")
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
            print(f"文字提取失败: {traceback.format_exc()}")
            # 如果BeautifulSoup失败，使用简单的正则表达式
            try:
                # 移除HTML标签
                text = re.sub(r'<[^>]+>', '', html_content)
                # 移除多余空白
                text = re.sub(r'\s+', ' ', text)
                return text.strip()
            except:
                return html_content
            
    async def get_announcement_detail(self, announcement_url):
        html_content = await self.get_page_content(announcement_url)
        
        soup = BeautifulSoup(html_content, 'html.parser')
        article_content = soup.find('article')
        text = self.extract_text_from_html(str(article_content))
        return {"text": text}
    
    
    
    async def run_scraping(self):
        try:
            await self.init_browser()
            announcements = await self.get_announcements_id()
            print("\n=== 公告列表 ===")
            
            # Counter for processed announcements in debug mode
            processed_count = 0
            
            for i, announcement in enumerate(announcements):
                # 获取公告详情
                article_id = announcement.get('id', '')
                # text_file_name = os.path.join(self.output_dir, f"bybit_{article_id}.txt")
                json_file_name = os.path.join(self.output_dir, f"okx_{article_id}.json")
                url = f"https://www.okx.com/zh-hans/help/{announcement.get('slug', '')}"
                print(f"   标题: {announcement.get('title', 'N/A')}")
                print(f"   URL: {url}")
                release_time = announcement.get('publishTime', '')
                release_time_str = pd.to_datetime(release_time, utc=True).tz_convert('Asia/Hong_Kong').strftime('%Y-%m-%d %H:%M:%S')
                if release_time_str < (pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)).strftime('%Y-%m-%d %H:%M:%S'):
                    print(f"公告 {announcement.get('title', 'N/A')} 发布时间 {release_time_str} 小于 {pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)}，跳过")
                    with open(json_file_name, 'w', encoding='utf-8') as f:
                        json.dump({'release_time': release_time_str, 'text': "", 'url': url, 'title': announcement.get('title', 'N/A'),"exchange": "okx"}, f, ensure_ascii=False, indent=4)
                    continue
                
                if os.path.exists(json_file_name):
                    print(f"公告详情已存在: {json_file_name}")
                    continue
                detail_result = await self.get_announcement_detail(url)
                text_content = detail_result.get('text', '')
                if detail_result:
                    print("\n=== 提取的文字数据 ===")
                    pprint.pprint(detail_result, indent=4)
                    # 保存JSON数据
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
                        self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'okx',
                            'title': announcement.get('title', 'N/A'),
                            'url': url,
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
                # if self.debug and processed_count >= self.max_size:
                #     break
        except Exception as e:
            print(f"获取Bybit公告详情失败: {traceback.format_exc()}")

if __name__ == "__main__":
    scraper = OkxScraper()
    scraper.run_scraping()
