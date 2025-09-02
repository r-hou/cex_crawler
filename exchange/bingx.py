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
import pandas as pd

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BingxScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10, offset_days: int = 7, analyzer_api_key= None):
        super().__init__("bingx", "https://www.bingx.com", analyzer, debug, max_size, offset_days, analyzer_api_key)
        

    
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
            self.log("ERROR", "未找到公告链接")
            exit()
        self.log("INFO", f"公告链接: {announcement_url}")
        
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
    
        self.log("INFO", f"Spot Listing URL: {spot_listing_url}")
        self.log("INFO", f"Future Listing URL: {future_listing_url}")
        self.log("INFO", f"Delisting URL: {delisting_url}")
        
        spot_listing_section_id = spot_listing_url.split("/")[-1]
        future_listing_section_id = future_listing_url.split("/")[-1]
        delisting_section_id = delisting_url.split("/")[-1]
        
        announcements = []
        
        # 方案1：监听网络请求
        for section_id, section_url in [
            (spot_listing_section_id, spot_listing_url),
            (future_listing_section_id, future_listing_url), 
            (delisting_section_id, delisting_url)
        ]:
            try:
                # 设置网络监听器
                api_responses = []
                
                async def handle_response(response):
                    if 'api/customer/v1/announcement/listArticles' in response.url:
                        try:
                            json_data = await response.json()
                            api_responses.append(json_data)
                        except:
                            pass
                
                # 注册响应监听器
                self.page.on('response', handle_response)
                
                # 访问页面，触发API请求
                await self.page.goto(section_url)
                await self.random_delay(3, 5)  # 等待页面完全加载
                
                # 尝试滚动页面，可能触发更多API请求
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.random_delay(2, 3)
                
                # 移除监听器
                self.page.remove_listener('response', handle_response)
                
                # 处理捕获的API响应
                for api_data in api_responses:
                    if api_data and 'data' in api_data and 'result' in api_data['data']:
                        section_announcements = api_data['data']['result']
                        # 为每个公告添加完整URL
                        for announcement in section_announcements:
                            if 'id' in announcement:
                                announcement['full_url'] = f"https://bingx.com/en/support/articles/{announcement['id']}"
                        
                        announcements.extend(section_announcements)
                
                await self.random_delay(2, 3)
                
            except Exception as e:
                self.log("ERROR", f"处理section {section_id} 时发生异常: {traceback.format_exc()}")
                continue
        
        # 如果网络监听没有获取到数据，尝试直接解析页面内容
        if not announcements:
            self.log("ERROR", "网络监听未获取到数据，尝试解析页面内容...")
            announcements = await self.parse_announcements_from_pages([
                spot_listing_url, future_listing_url, delisting_url
            ])
        
        return announcements

    async def parse_announcements_from_pages(self, urls):
        """从页面HTML中直接解析公告信息"""
        announcements = []
        
        for url in urls:
            try:
                await self.page.goto(url)
                await self.random_delay(3, 5)
                
                # 等待内容加载
                await self.page.wait_for_selector('.article-item, .announcement-item, .notice-item', timeout=10000)
                
                # 获取页面内容
                content = await self.page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # 尝试不同的选择器来找到公告列表
                selectors = [
                    '.article-item a',
                    '.announcement-item a', 
                    '.notice-item a',
                    'a[href*="/support/articles/"]',
                    'a[href*="/support/notice/"]'
                ]
                
                for selector in selectors:
                    links = soup.select(selector)
                    if links:
                        for link in links:
                            title = link.get_text(strip=True)
                            href = link.get('href', '')
                            
                            if href and title:
                                if not href.startswith('http'):
                                    href = 'https://bingx.com' + href
                                
                                announcements.append({
                                    'title': title,
                                    'full_url': href,
                                    'id': href.split('/')[-1] if '/' in href else ''
                                })
                        break
                
            except Exception as e:
                self.log("ERROR", f"解析页面 {url} 时出错: {traceback.format_exc()}")
                continue
        
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
            self.log("ERROR", f"文字提取失败: {traceback.format_exc()}")
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
            else:
                # 如果没找到article-body，使用整个页面内容
                self.log("ERROR", "未找到article-body标签，使用整个页面内容")
                text_content = self.extract_text_from_html(content)

            return {
                'html': content,
                'text': text_content
            }
            
        except Exception as e:
            self.log("ERROR", f"获取公告详情失败: {traceback.format_exc()}")
            return None
    
    
    
    async def run_scraping(self):
        """运行爬虫主流程"""
        try:
            await self.init_browser()
            
            self.log("INFO", f"开始抓取 {self.exchange_name} 公告", console=True)
            
            # 获取公告列表
            announcements = await self.get_announcements_id()

            if not announcements:
                self.log("ERROR", "未获取到公告", console=True)
                return
            
            # 限制调试模式下的处理数量
            # announcements = self.limit_results_for_debug(announcements)
            # print(announcements)
            processed_count = 0
            for i, article in enumerate(announcements):
                try:
                    title = article.get('title', 'N/A')
                    full_url = f"https://bingx.com/en/support/articles/{article.get('articleId', '')}"
                    
                    if not full_url:
                        continue
                        
                    self.log("INFO", f"处理公告 {i+1}/{len(announcements)}: {title}", console=True)
                    
                    # 生成文件ID
                    file_id = article.get('articleId', '')
                    json_filepath = os.path.join(self.output_dir, f"bingx_{file_id}.json")
                    release_time = article.get('updateTime', '')
                    release_time_str = pd.to_datetime(release_time).tz_convert('Asia/Hong_Kong').strftime('%Y-%m-%d %H:%M:%S')
                    if release_time_str < (pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)).strftime('%Y-%m-%d %H:%M:%S'):
                        self.log("INFO", f"公告 {title} 发布时间 {release_time_str} 小于 {pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)}，跳过", console=True)
                        with open(json_filepath, 'w', encoding='utf-8') as f:
                            json.dump({'release_time': release_time_str, 'text': "", 'url': full_url, 'title': title,"exchange": "bingx"}, f, ensure_ascii=False, indent=4)
                        continue
                    
                    # 检查文件是否已存在
                    # text_filepath = os.path.join(self.output_dir, f"bingx_{file_id}.txt")
                    
                    
                    if os.path.exists(json_filepath):
                        self.log("INFO", f"公告详情已存在，跳过", console=True)
                        continue
                    
                    # 获取公告详情
                    detail_result = await self.get_announcement_detail(full_url)
                    if not detail_result:
                        self.log("ERROR", "获取详情失败")
                        continue
                    
                    text_content = detail_result['text']
                    if not text_content.strip():
                        self.log("ERROR", "文本内容为空")
                        continue
                    analysis_result = self.analyzer.analyze_announcement(text_content)
                    
                    # 显示分析结果
                    self.analyzer.print_analysis_result(analysis_result)
                    
                    # 保存分析结果
                    self.analyzer.save_analysis_result(analysis_result, json_filepath, updates={
                            'title': title,
                            'exchange': 'bingx',
                            'url': full_url,
                            "release_time": release_time_str,
                            "content": text_content
                        })

    
                    
                    processed_count += 1
                    # if self.debug and processed_count >= self.max_size:
                    #     print(f"Debug mode: Reached max_size limit ({self.max_size}), stopping...")
                    #     break
                    await self.random_delay(2, 5)
                    
                except Exception as e:
                    self.log("ERROR", f"处理公告时出错: {traceback.format_exc()}")
                    continue
            
            self.log("INFO", f"{self.exchange_name} 抓取完成，共处理 {processed_count} 个公告")
            
        except Exception as e:
            self.log("ERROR", f"程序执行出错: {traceback.format_exc()}", console=True)
        finally:
            await self.cleanup_browser()

async def main():
    """主函数，创建爬虫实例并运行"""
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = BingxScraper(analyzer, debug=True, max_size=3)  # Debug mode for testing
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
