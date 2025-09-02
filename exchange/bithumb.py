import asyncio
import time
import random
import json
# from pprint import pprint
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

class BithumbScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10, offset_days: int = 7):
        super().__init__("bithumb", "https://www.bithumb.com", analyzer, debug, max_size, offset_days)
        

    
    
    async def handle_cloudflare_protection(self, url, max_retries=3):
        """处理Cloudflare保护"""
        for attempt in range(max_retries):
            try:
                self.log("INFO", f"尝试访问 {url} (第 {attempt + 1} 次)", console=True)
                
                # 导航到页面
                await self.page.goto(url, wait_until='domcontentloaded')
                await self.random_delay(3, 5)
                
                # 检查是否遇到Cloudflare保护页面
                page_content = await self.page.content()
                if "Attention Required!" in page_content or "Cloudflare" in page_content:
                    self.log("WARNING", "检测到Cloudflare保护页面，等待处理...", console=True)
                    
                    # 等待Cloudflare检查完成
                    try:
                        # 等待页面加载完成或超时
                        await self.page.wait_for_load_state('networkidle', timeout=30000)
                        await self.random_delay(5, 10)
                        
                        # 检查是否还有Cloudflare页面
                        current_content = await self.page.content()
                        if "Attention Required!" not in current_content and "Cloudflare" not in current_content:
                            self.log("INFO", "Cloudflare检查完成，页面已正常加载", console=True)
                            return await self.page.content()
                        else:
                            self.log("WARNING", "Cloudflare检查仍在进行，继续等待...")
                            await self.random_delay(10, 15)
                            
                    except Exception as e:
                        self.log("ERROR", f"等待Cloudflare检查时出错: {traceback.format_exc()}")
                        await self.random_delay(5, 8)
                else:
                    self.log("INFO", "页面正常加载，未遇到Cloudflare保护")
                    return await self.page.content()
                    
            except Exception as e:
                self.log("ERROR", f"第 {attempt + 1} 次尝试失败: {traceback.format_exc()}")
                if attempt < max_retries - 1:
                    await self.random_delay(5, 10)
                else:
                    raise e
        
        raise Exception("无法绕过Cloudflare保护")

    
        
    async def get_announcements_id(self, catalog_id='161', page_no='1', page_size='10'):
        """获取公告列表"""

        content = await self.get_page_content('https://feed.bithumb.com/notice', 'load')
        json_data = self.extract_json_from_script(content)
        self.build_id = json_data['buildId']
        delisting_url = f'https://feed.bithumb.com/notice?category=6&page=1'
        listing_url = f'https://feed.bithumb.com/notice?category=1&page=1'
        listing_content = await self.get_page_content(listing_url, 'load')
        with open('listing_content.html', 'w') as f:
            f.write(listing_content)
        listing_json_data = self.get_json_from_html(listing_content)
        # pprint(listing_json_data)
        announcements_listing = listing_json_data['props']['pageProps']['noticeList']
        announcements_listing = [ i for i in announcements_listing if i['categoryName1'] in ["안내", "거래지원종료"]]
        
        delisting_content = await self.get_page_content(delisting_url, 'load')
        delisting_json_data = self.get_json_from_html(delisting_content)
        announcements_delisting = delisting_json_data['props']['pageProps']['noticeList']
        announcements_delisting = [ i for i in announcements_delisting if i['categoryName1'] in ["안내", "거래지원종료"]]
        # pprint(announcements_listing)
        # pprint(announcements_delisting)
        return announcements_listing + announcements_delisting


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
                    print(f"解析 __NEXT_DATA__ JSON失败: {traceback.format_exc()}")
            
            
            if not json_data:
                print("未找到script标签中的JSON数据")
            
            return json_data
            
        except Exception as e:
            print(f"提取script标签JSON数据失败: {traceback.format_exc()}")
            return {}
        
        

    async def get_page_content(self, url, state='load'):
        """获取页面内容"""
        try:
            # 使用Cloudflare保护处理方法
            content = await self.handle_cloudflare_protection(url)
            return content
        except Exception as e:
            print(f"获取页面内容失败: {traceback.format_exc()}")
            # 如果Cloudflare处理失败，尝试传统方法
            await self.page.goto(url)
            await self.random_delay(2, 4)
            await self.page.wait_for_load_state(state)
            return await self.page.content()
    
    async def get_announcement_detail(self, article_id):
        """获取公告详情"""
        print(f"正在获取公告详情: {article_id}")
        
        try:
            # 方法1: 使用page.evaluate()发送POST请求
            api_url = f"https://feed.bithumb.com/notice/{article_id}"
            content = await self.get_page_content(api_url, 'load')
            json_data = self.get_json_from_html(content)


            text_content = json_data['props']['pageProps']['data']['title']  + "\n" + self.parse_announcement_content(json_data['props']['pageProps']['data']['content']) 

            return {
                'html': content,
                'text': text_content
            }
            
        except Exception as e:
            print(f"获取公告详情失败: {traceback.format_exc()}")
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
                text_file_name = os.path.join(self.output_dir, f"bithumb_{article_id}.txt")
                json_file_name = os.path.join(self.output_dir, f"bithumb_{article_id}.json")
                if os.path.exists(text_file_name) and os.path.exists(json_file_name):
                    print(f"公告详情已存在: {text_file_name}")
                    continue
                print("=== 获取公告详情 ===")
                print(f"   标题: {article.get('title', 'N/A')}")
                print(f"   URL: https://feed.bithumb.com/notice/{article_id}")
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
                            self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'bithumb'})
                            
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
    scraper = BithumbScraper(analyzer, debug=True, max_size=3)
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
