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

class WeexScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10):
        super().__init__("weex", "https://www.weex.com", analyzer, debug, max_size)
        

    
    
    async def get_announcements_id(self, catalog_id='161', page_no='1', page_size='10'):
        """获取公告列表"""
        content = await self.get_page_content('https://weexsupport.zendesk.com/hc/en-us', 'load')

        # with open('weex_announcements.html', 'w') as f:
        #     f.write(content)
            # 解析HTML
        soup = BeautifulSoup(content, 'html.parser')
        
        # 查找所有class为promoted-articles-item的li标签
        promoted_items = soup.find_all('li', class_='promoted-articles-item')
        
        print(f"找到 {len(promoted_items)} 个promoted-articles-item")
        
        # 提取每个item下的a标签href
        links = []
        for i, item in enumerate(promoted_items):
            # 查找item下的a标签
            a_tag = item.find('a')
            if a_tag:
                href = a_tag.get('href')
                text = a_tag.get_text(strip=True)
                if "listing" in text.lower():
                    link_info = {
                        'index': i + 1,
                        'href': href,
                        'title': text,
                        'full_url': f"https://weexsupport.zendesk.com/{href}" if href and href.startswith('/') else href
                    }
                    links.append(link_info)
        return links

        
        

    async def get_page_content(self, url, state='load'):
        """获取页面内容"""
        await self.page.goto(url)
        await self.random_delay(2, 4)
        await self.page.wait_for_load_state(state)
        return await self.page.content()
    
    async def get_announcement_detail(self, full_url):
        """获取公告详情"""
        print(f"正在获取公告详情: {full_url}")
        
        try:
            content = await self.get_page_content(full_url, 'load')
            
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # 查找class为"article-body"的div标签
            article_body = soup.find('div', class_='article-body')
            
            if article_body:
                # 将article-body div及其子标签转换为字符串
                article_body_html = str(article_body)
                text_content = self.parse_announcement_content(article_body_html)
                print("成功找到article-body标签")
            else:
                # 如果没找到article-body，使用整个页面内容
                print("未找到article-body标签，使用整个页面内容")
                text_content = self.parse_announcement_content(content)

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
                full_url = article.get('full_url')
                article_id = md5(full_url.encode('utf-8')).hexdigest()
                text_file_name = os.path.join(self.output_dir, f"weex_{article_id}.txt")
                json_file_name = os.path.join(self.output_dir, f"weex_{article_id}.json")
                if os.path.exists(text_file_name) and os.path.exists(json_file_name):
                    print(f"公告详情已存在: {text_file_name}")
                    continue
                
                print("=== 获取公告详情 ===")
                print(f"   标题: {article.get('title', 'N/A')}")
                print(f"   URL: {article.get('full_url')}")
                if full_url:
                    detail_result = await self.get_announcement_detail(full_url)
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
                            self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'weex'})
                            
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
    scraper = WeexScraper(analyzer, debug=True, max_size=3)
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
