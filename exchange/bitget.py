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

from .base_scraper import BaseScraper
from deepseek_analyzer import DeepSeekAnalyzer
import traceback

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BitgetScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10):
        super().__init__("bitget", "https://www.bitget.com", analyzer, debug, max_size)
        

    
    
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

        content = await self.get_page_content('https://www.bitget.com/support/announcement-center', 'load')
        json_data = self.extract_json_from_script(content)
        self.build_id = json_data['buildId']
        print(f"Build ID: {self.build_id}")
        # with open('bitget_announcements.json', 'w') as f:
        #     json.dump(json_data, f, ensure_ascii=False, indent=2)
        json_data = json_data['props']['pageProps']['originCategory']['navigationList']
        # print(json_data)
  
        spot_listing_section_id, futures_listing_section_id, delisting_section_id = None, None, None
        for i in json_data:
            if "new listing" in i['navigationName'].lower():
                sectionList = i['sectionList']
                for j in sectionList:
                    if j['sectionName'] == 'Spot':
                        spot_listing_section_id = j['sectionPid']
                    elif j['sectionName'] == 'Futures':
                        futures_listing_section_id = j['sectionPid']
            if "delisting" in i['navigationName'].lower():
                delisting_section_id = i['sectionList'][0]['sectionPid']
        print(f"Spot listing section ID: {spot_listing_section_id}")
        print(f"Futures listing section ID: {futures_listing_section_id}")
        print(f"Delisting section ID: {delisting_section_id}")
        spot_listing_url = f'https://www.bitget.com/support/_next/data/Xt6R0Fqn1UDxRwqoNVED5/en/support/sections/{spot_listing_section_id}/1.json?slug={spot_listing_section_id}&slug=1'
        futures_listing_url = f'https://www.bitget.com/support/_next/data/Xt6R0Fqn1UDxRwqoNVED5/en/support/sections/{futures_listing_section_id}/1.json?slug={futures_listing_section_id}&slug=1'
        delisting_url = f'https://www.bitget.com/support/_next/data/Xt6R0Fqn1UDxRwqoNVED5/en/support/sections/{delisting_section_id}/1.json?slug={delisting_section_id}&slug=1'
        spot_listing_content = await self.get_page_content(spot_listing_url, 'load')
        futures_listing_content = await self.get_page_content(futures_listing_url, 'load')
        delisting_content = await self.get_page_content(delisting_url, 'load')
        spot_listing_json_data = self.get_json_from_html(spot_listing_content)
        futures_listing_json_data = self.get_json_from_html(futures_listing_content)
        delisting_json_data = self.get_json_from_html(delisting_content)
        announcements = spot_listing_json_data['pageProps']['sectionArticle']['items'] + futures_listing_json_data['pageProps']['sectionArticle']['items'] + delisting_json_data['pageProps']['sectionArticle']['items']
        return announcements


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
            # 方法1: 使用page.evaluate()发送POST请求
            api_url = f"https://www.bitget.com/support/_next/data/{self.build_id}/en/support/articles/{article_id}.json?contentId={article_id}"
            content = await self.get_page_content(api_url, 'load')
            json_data = self.get_json_from_html(content)


            text_content = json_data['pageProps']['details']['title']  + "\n" + self.parse_announcement_content(json_data['pageProps']['details']['content']) 

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
                article_id = article.get('simpleResult').get('contentId')
                text_file_name = os.path.join(self.output_dir, f"bitget_{article_id}.txt")
                json_file_name = os.path.join(self.output_dir, f"bitget_{article_id}.json")
                if os.path.exists(text_file_name) and os.path.exists(json_file_name):
                    print(f"公告详情已存在: {text_file_name}")
                    continue
                print("=== 获取公告详情 ===")
                print(f"   标题: {article.get('title', 'N/A')}")
                print(f"   URL: https://www.bitget.com/support/articles/{article_id}")
                if article_id:
                    detail_result = await self.get_announcement_detail(article_id)
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
                            self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'bitget'})
                            
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
            print(f"程序执行出错: {traceback.format_exc()}")
        
        finally:
            # 关闭浏览器
            await self.cleanup_browser()

async def main():
    """主函数，创建爬虫实例并运行"""
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = BitgetScraper(analyzer, debug=True, max_size=3)
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
