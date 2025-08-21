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
from hashlib import md5

from .base_scraper import BaseScraper
from deepseek_analyzer import DeepSeekAnalyzer
import traceback

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CoinexScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10):
        super().__init__("coinex", "https://www.coinex.com", analyzer, debug, max_size)
        

    
    
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
        content = await self.get_page_content('https://www.coinex.com/en/announcements', 'load')


        
        soup = BeautifulSoup(content, 'html.parser')
        
        # 查找所有class为promoted-articles-item的li标签
        promoted_items = soup.find_all('a')

        
        listting_section_id, delisting_section_id = "", ""
        for i, a_tag in enumerate(promoted_items):
            href = a_tag.get('href')
            span_tag = a_tag.find('span')
            if span_tag:
                text = span_tag.get_text(strip=True)
            else:
                continue
            if "new listing" in text.lower():
                listting_section_id = href.split('=')[-1]
            elif "delisting" in text.lower():
                delisting_section_id = href.split('=')[-1]
        
        if len(listting_section_id) == 0 or len(delisting_section_id) == 0:
            print("未找到coinex公告链接")
            exit()
        
        listting_url = f"https://www.coinex.com/res/support/zendesk/articles/new?limit=15&page=1&section_id={listting_section_id}&order_by=is_top"
        delisting_url = f"https://www.coinex.com/res/support/zendesk/articles/new?limit=15&page=1&section_id={delisting_section_id}&order_by=is_top"

        listting_content = await self.get_page_content(listting_url, 'load')
        delisting_content = await self.get_page_content(delisting_url, 'load')
        listing_json_data = self.get_json_from_html(listting_content)
        delisting_json_data = self.get_json_from_html(delisting_content)
        announcements = listing_json_data['data']['data'] + delisting_json_data['data']['data']
        return announcements

        
        

    async def get_page_content(self, url, state='load'):
        """获取页面内容"""
        await self.page.goto(url)
        await self.random_delay(2, 4)
        await self.page.wait_for_load_state(state)
        return await self.page.content()
    
    async def get_announcement_detail(self, article_body):
        """获取公告详情"""
        
        try:
            text_content = self.parse_announcement_content(article_body)

            return {
                'html': article_body,
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
                text_file_name = os.path.join(self.output_dir, f"coinex_{article_id}.txt")
                json_file_name = os.path.join(self.output_dir, f"coinex_{article_id}.json")
                if os.path.exists(text_file_name) and os.path.exists(json_file_name):
                    print(f"公告详情已存在: {text_file_name}")
                    continue
                print("=== 获取公告详情 ===")
                print(f"   标题: {article.get('title', 'N/A')}")
                print(f"   URL: https://www.coinex.com/en/announcements/detail/{article_id}")
                detail_result = await self.get_announcement_detail(article.get('body'))
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
                        self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'coinex'})
                        
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
    scraper = CoinexScraper(analyzer, debug=True, max_size=3)
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
