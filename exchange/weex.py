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
import pandas as pd

from .base_scraper import BaseScraper
from deepseek_analyzer import DeepSeekAnalyzer
import traceback

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WeexScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10, offset_days: int = 7, analyzer_api_key= None):
        super().__init__("weex", "https://www.weex.com", analyzer, debug, max_size, offset_days, analyzer_api_key)
        

    
    
    async def get_announcements_id(self, catalog_id='161', page_no='1', page_size='10'):
        """获取公告列表"""
        content = await self.get_page_content('https://weexsupport.zendesk.com/hc/en-us', 'load')

        # with open('weex_announcements.html', 'w') as f:
        #     f.write(content)
            # 解析HTML
        soup = BeautifulSoup(content, 'html.parser')
        
        # 查找所有class为promoted-articles-item的li标签
        promoted_items = soup.find_all('li', class_='promoted-articles-item')
        
        self.log("INFO", f"找到 {len(promoted_items)} 个promoted-articles-item")
        
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
        self.log("INFO", f"正在获取公告详情: {full_url}")
        
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
                self.log("DEBUG", "成功找到article-body标签")
            else:
                # 如果没找到article-body，使用整个页面内容
                self.log("WARNING", "未找到article-body标签，使用整个页面内容")
                text_content = self.parse_announcement_content(content)

            # 修复获取时间的代码
            try:
                article_author = soup.find("div", class_="article-author")
                if article_author:
                    time_element = article_author.find("time")
                    if time_element:
                        release_time = time_element.get("datetime")  # 使用.get()而不是.get_attribute()
                        self.log("DEBUG", f"release_time: {release_time}")
                    else:
                        self.log("WARNING", "未找到time元素")
                        release_time = None
                else:
                    self.log("WARNING", "未找到article-author元素")
                    release_time = None
            except Exception as e:
                self.log("ERROR", f"获取release_time时出错: {traceback.format_exc()}")
                release_time = None


            return {
                'html': content,
                'text': text_content,
                'release_time': release_time
            }
            
        except Exception as e:
            self.log("ERROR", f"获取公告详情失败: {traceback.format_exc()}")
            return None
    
    
    
    async def run_scraping(self):
        """运行爬虫主流程"""
        try:
            # 初始化浏览器
            await self.init_browser()
            
            # 获取公告分类数据
            announcements = await self.get_announcements_id()
            
            if not announcements:
                self.log("ERROR", "未获取到公告", console=True)
                return
            
            # Counter for processed announcements in debug mode
            processed_count = 0
            
            for i, article in enumerate(announcements):
                self.log("INFO", f"处理公告 {i+1}/{len(announcements)}: {article.get('title', 'N/A')}", console=True)
                full_url = article.get('full_url')
                article_id = md5(full_url.encode('utf-8')).hexdigest()
                # text_file_name = os.path.join(self.output_dir, f"weex_{article_id}.txt")
                json_file_name = os.path.join(self.output_dir, f"weex_{article_id}.json")
                if os.path.exists(json_file_name):
                    self.log("INFO", f"公告详情已存在: {json_file_name}")
                    continue
                
                self.log("INFO", "=获取公告详情")
                self.log("INFO", f"   标题: {article.get('title', 'N/A')}")
                self.log("INFO", f"   URL: {article.get('full_url')}")
                if full_url:
                    detail_result = await self.get_announcement_detail(full_url)
                    if detail_result:
                        release_time = detail_result['release_time']
                        release_time_str = pd.to_datetime(release_time, utc=True).tz_convert('Asia/Hong_Kong').strftime('%Y-%m-%d %H:%M:%S')
                        if release_time_str < (pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)).strftime('%Y-%m-%d %H:%M:%S'):
                            self.log("INFO", f"公告 {article.get('title', 'N/A')} 发布时间 {release_time_str} 小于 {pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)}，跳过", console=True)
                            with open(json_file_name, 'w', encoding='utf-8') as f:
                                json.dump({'release_time': release_time_str, 'text': "", 'url': full_url, 'title': article.get('title', 'N/A'),"exchange": "weex"}, f, ensure_ascii=False, indent=4)
                            continue
                        text_content = detail_result['text']
                        self.log("INFO", "纯文字内容")
                        self.log("INFO", text_content[:1000] + "..." if len(text_content) > 1000 else text_content)
                        
                        # 保存到文件
                        # with open(text_file_name, 'w', encoding='utf-8') as f:
                        #     f.write(text_content)
                        # print(f"\n纯文字内容已保存到: {text_file_name}")
                        
                        # 使用OpenAI分析内容
                        self.log("INFO", "使用DeepSeek分析公告内容")
                        try:
                            # analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
                            analysis_result = self.analyzer.analyze_announcement(text_content)

                            
                            # 显示分析结果
                            self.analyzer.print_analysis_result(analysis_result)
                            
                            # 保存分析结果
                            self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'weex',
                                'title': article.get('title', 'N/A'),
                                'url': full_url,
                                'release_time': release_time_str,
                                'content': text_content
                            })
                            
                            # Increment counter for successfully processed announcements
                            processed_count += 1
                            # if self.debug and processed_count >= self.max_size:
                            #     print(f"Debug mode: Reached max_size limit ({self.max_size}), stopping...")
                            #     break
                            
                        except Exception as e:
                            self.log("ERROR", f"DeepSeek分析失败: {traceback.format_exc()}", console=True)
                    else:
                        self.log("ERROR", "获取详情失败", console=True)
                
                # Break outer loop if we've reached max_size in debug mode
                # if self.debug and processed_count >= self.max_size:
                #     break
            
        except Exception as e:
            self.log("ERROR", f"程序执行出错: {traceback.format_exc()}", console=True)
        
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
