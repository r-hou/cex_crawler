import asyncio
import time
import random
import json
from pprint import pprint
from playwright.async_api import async_playwright
import urllib3
import requests
import re
from bs4 import BeautifulSoup
import os
import sys
import pandas as pd

from .base_scraper import BaseScraper
from deepseek_analyzer import DeepSeekAnalyzer
import traceback

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MexcScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10, offset_days: int = 7, analyzer_api_key= None):
        super().__init__("mexc", "https://www.mexc.com", analyzer, debug, max_size, offset_days, analyzer_api_key)
        

    
    
    def get_json_from_html(self, html_content):
        """从HTML内容中提取JSON数据"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            pre_tag = soup.find('pre')
            if pre_tag and pre_tag.string:
                return json.loads(pre_tag.string.strip())
        except json.JSONDecodeError as e:
            print(f"从<pre>标签解析JSON失败: {e}")
            print("返回HTML内容供调试")
            return html_content
        except Exception as e:
            print(f"解析页面内容失败: {e}")
            return html_content
        
    async def get_announcements_id(self, catalog_id='161', page_no='1', page_size='10'):
        """获取公告列表"""

        content = await self.get_page_content('https://www.mexc.com/zh-MY/', 'load')
        # find "公告中心" href
        soup = BeautifulSoup(content, 'html.parser')
        href = soup.find('a', string='公告中心')['href']
        
        category_id = href.split('/')[-1]
        api_url = f'https://www.mexc.com/help/announce/api/zh-MY/section/{category_id}/sections?showAllSectionWithArticle=true'
        content = await self.get_page_content(api_url, 'load')
        json_data = self.get_json_from_html(content)
        listing_section_id, delisting_section_id = None, None
        for i in json_data['data']:
            if i['name'] == '上币信息':
                listing_section_id = i['id']
            elif i['name'] == '币种下架':
                delisting_section_id = i['id']
        print(f"Listing section ID: {listing_section_id}")
        print(f"Delisting section ID: {delisting_section_id}")
        listing_url = f'https://www.mexc.com/help/announce/api/zh-MY/section/{listing_section_id}/articles?page=1&perPage=20'
        delisting_url = f'https://www.mexc.com/help/announce/api/zh-MY/section/{delisting_section_id}/articles?page=1&perPage=20'
        listing_content = await self.get_page_content(listing_url, 'load')
        delisting_content = await self.get_page_content(delisting_url, 'load')
        listing_json_data = self.get_json_from_html(listing_content)
        delisting_json_data = self.get_json_from_html(delisting_content)
        announcements = listing_json_data['data']['results'] + delisting_json_data['data']['results']
        return announcements

    
    

    async def get_page_content(self, url, state='load'):
        """获取页面内容"""
        await self.page.goto(url)
        await self.random_delay(2, 4)
        await self.page.wait_for_load_state(state)
        return await self.page.content()
    
    async def get_announcement_detail(self, article_id):
        """获取公告详情"""
        print(f"正在获取公告详情: {article_id}")
        
        try:
            content = await self.get_page_content(f'https://www.mexc.com/help/announce/api/zh-MY/article/{article_id}', 'load')
            json_data = self.get_json_from_html(content)
            text_content = json_data['data']['title'] + "\n" + self.parse_announcement_content(json_data['data']['body'])
            
            print("成功获取公告详情")
            return {
                'html': content,
                'text': text_content
            }
            
        except Exception as e:
            print(f"获取公告详情失败: {e}")
            return None
    
    
    
    async def run_scraping(self):
        """运行爬虫主流程"""
        try:
            # 初始化浏览器
            await self.init_browser()
            
            # 获取公告分类数据
            announcements = await self.get_announcements_id()
            
            if not announcements:
                print("未获取到公告")
                return
            
            # Counter for processed announcements in debug mode
            processed_count = 0
            
            for i, article in enumerate(announcements):
                article_id = article.get('id')
                # text_file_name = os.path.join(self.output_dir, f"mexc_{article_id}.txt")
                json_file_name = os.path.join(self.output_dir, f"mexc_{article_id}.json")
                url = f"https://www.mexc.com/zh-MY/support/articles/{article_id}"
                release_time = article.get('createdAt')
                release_time_str = pd.to_datetime(release_time).tz_convert('Asia/Hong_Kong').strftime('%Y-%m-%d %H:%M:%S')
                if release_time_str < (pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)).strftime('%Y-%m-%d %H:%M:%S'):
                    print(f"公告 {article.get('title', 'N/A')} 发布时间 {release_time_str} 小于 {pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)}，跳过")
                    continue
                if os.path.exists(json_file_name):
                    print(f"公告详情已存在: {json_file_name}")
                    continue
                print(f"   标题: {article.get('title', 'N/A')}")
                print(f"   URL: {url}")
                if article_id:
                    print("=== 获取公告详情 ===")
                    detail_result = await self.get_announcement_detail(article_id)
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
                            self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'mexc',
                                'title': article.get('title', 'N/A'),
                                'url': f"https://www.mexc.com/zh-MY/support/articles/{article_id}",
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
                        print("获取详情失败")
                
                # Break outer loop if we've reached max_size in debug mode
                if self.debug and processed_count >= self.max_size:
                    break
            
        except Exception as e:
            print(f"程序执行出错: {e}")
        
        finally:
            # 关闭浏览器
            await self.cleanup_browser()

async def main():
    """主函数，创建爬虫实例并运行"""
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = MexcScraper(analyzer, debug=True, max_size=3)
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
