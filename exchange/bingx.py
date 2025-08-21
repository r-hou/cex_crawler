import asyncio
import time
import random
import json
import hashlib
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

class BingxScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10):
        super().__init__("bingx", "https://www.bingx.com", analyzer, debug, max_size)
        

    
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
    
    def get_announcement_url(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        li_tags = soup.find_all('li', class_="article-item")
        announcements = []
        for li_tag in li_tags:
            a_tag = li_tag.find('a')
            announcements.append({
                "title": a_tag.get_text(strip=True),
                "full_url": "https://bingx.com" + a_tag.get('href')
            })
        return announcements
    
    async def get_announcements_id(self, catalog_id='161', page_no='1', page_size='10'):
        """获取公告列表"""

        content = await self.get_page_content('https://bingx.com/en', 'load')
        # find "公告中心" href
        soup = BeautifulSoup(content, 'html.parser')
        announcement_url = ""
        a_tags = soup.find_all('a')
        for a_tag in a_tags:
            if "announcement" in a_tag.get_text(strip=True).lower():
                announcement_url = a_tag.get('href')
                break
        if len(announcement_url) == 0:
            print("未找到公告链接")
            exit()
        print(f"公告链接: {announcement_url}")
        
        while announcement_url[-1] == '/':
            announcement_url = announcement_url[:-1]
        
        content = await self.get_page_content(announcement_url, 'load')
        soup = BeautifulSoup(content, 'html.parser')
        a_tags = soup.find_all('a', class_="tab-list__item")
        spot_listing_url, future_listing_url, delisting_url = "", "", ""
        for a_tag in a_tags:
            if "spot listing" in a_tag.get_text(strip=True).lower():
                spot_listing_url = "https://bingx.com" + a_tag.get('href')
            if "futures listing" in a_tag.get_text(strip=True).lower():
                future_listing_url = "https://bingx.com" + a_tag.get('href')
            if "delisting" in a_tag.get_text(strip=True).lower():
                delisting_url = "https://bingx.com" + a_tag.get('href')
        print(f"Spot Listing URL: {spot_listing_url}")
        print(f"Future Listing URL: {future_listing_url}")
        print(f"Delisting URL: {delisting_url}")
        spot_listing_content = await self.get_page_content(spot_listing_url, 'load')
        future_listing_content = await self.get_page_content(future_listing_url, 'load')
        delisting_content = await self.get_page_content(delisting_url, 'load')
        spot_listing_announcements = self.get_announcement_url(spot_listing_content)
        future_listing_announcements = self.get_announcement_url(future_listing_content)
        delisting_announcements = self.get_announcement_url(delisting_content)
        announcements = spot_listing_announcements + future_listing_announcements + delisting_announcements
        return announcements

    
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
            print(f"文字提取失败: {e}")
            # 如果BeautifulSoup失败，使用简单的正则表达式
            try:
                # 移除HTML标签
                text = re.sub(r'<[^>]+>', '', html_content)
                # 移除多余空白
                text = re.sub(r'\s+', ' ', text)
                return text.strip()
            except:
                return html_content


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
            article_body = soup.find("div", class_="article-body")
            
            if article_body:
                # 将article-body div及其子标签转换为字符串
                article_body_html = str(article_body)
                text_content = self.extract_text_from_html(article_body_html)
                print("成功找到article-body标签")
            else:
                # 如果没找到article-body，使用整个页面内容
                print("未找到article-body标签，使用整个页面内容")
                text_content = self.extract_text_from_html(content)

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
            await self.init_browser()
            
            print(f"=== 开始抓取 {self.exchange_name} 公告 ===")
            
            # 获取公告列表
            announcements = await self.get_announcements_id()
            
            if not announcements:
                print("未获取到公告")
                return
            
            # 限制调试模式下的处理数量
            announcements = self.limit_results_for_debug(announcements)
            
            processed_count = 0
            for i, article in enumerate(announcements):
                try:
                    full_url = article.get('full_url')
                    title = article.get('title', 'N/A')
                    
                    if not full_url:
                        continue
                        
                    print(f"\n处理公告 {i+1}/{len(announcements)}: {title}")
                    
                    # 生成文件ID
                    file_id = self.generate_file_id(full_url)
                    
                    # 检查文件是否已存在
                    text_filepath = os.path.join(self.output_dir, f"bingx_{file_id}.txt")
                    json_filepath = os.path.join(self.output_dir, f"bingx_{file_id}.json")
                    
                    if os.path.exists(text_filepath) and os.path.exists(json_filepath):
                        print(f"公告详情已存在，跳过")
                        continue
                    
                    # 获取公告详情
                    detail_result = await self.get_announcement_detail(full_url)
                    if not detail_result:
                        print("获取详情失败")
                        continue
                    
                    text_content = detail_result['text']
                    if not text_content.strip():
                        print("文本内容为空")
                        continue
                    
                    # 使用基类方法分析和保存
                    self.analyze_and_save_announcement(
                        text_content,
                        {
                            'title': title,
                            'url': full_url
                        }
                    )
                    
                    processed_count += 1
                    await self.random_delay(2, 5)
                    
                except Exception as e:
                    print(f"处理公告时出错: {e}")
                    continue
            
            print(f"\n=== {self.exchange_name} 抓取完成，共处理 {processed_count} 个公告 ===")
            
        except Exception as e:
            print(f"程序执行出错: {e}")
            traceback.print_exc()
        finally:
            await self.cleanup_browser()

async def main():
    """主函数，创建爬虫实例并运行"""
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = BingxScraper(analyzer, debug=True, max_size=3)  # Debug mode for testing
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
