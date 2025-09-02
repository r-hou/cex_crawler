import asyncio
import time
import random
import json
import uuid
import hashlib
import base64
from pprint import pprint
from playwright.async_api import async_playwright
import urllib3
import requests
import re
from bs4 import BeautifulSoup
from deepseek_analyzer import DeepSeekAnalyzer
import traceback
import os
from .base_scraper import BaseScraper
import pandas as pd

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BinanceScraper(BaseScraper):
    def __init__(self, analyzer: DeepSeekAnalyzer, debug: bool = False, max_size: int = 10, offset_days: int = 7, analyzer_api_key= None):
        super().__init__("binance", "https://www.binance.com", analyzer, debug, max_size, offset_days, analyzer_api_key)
        
    
    def generate_uuid(self):
        """生成UUID"""
        return str(uuid.uuid4())
    
    def generate_csrf_token(self):
        """生成CSRF token"""
        timestamp = str(int(time.time() * 1000))
        return hashlib.md5(timestamp.encode()).hexdigest()
    
    def generate_device_info(self):
        """生成设备信息"""
        
        device_info = {
            "screen_resolution": "1920,1080",
            "available_screen_resolution": "995,1920",
            "system_version": "Mac OS 10.15.7",
            "brand_model": "unknown",
            "system_lang": "en-US",
            "timezone": "GMT+08:00",
            "timezoneOffset": -480,
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "list_plugin": "PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF",
            "canvas_code": "ddf8dc45",
            "webgl_vendor": "Google Inc. (Apple)",
            "webgl_renderer": "ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)",
            "audio": "124.04346607114712",
            "platform": "MacIntel",
            "web_timezone": "Asia/Hong_Kong",
            "device_name": "Chrome V134.0.0.0 (Mac OS)",
            "fingerprint": "677f6a4834426e455f7cd71f95bb2bda",
            "device_id": "",
            "related_device_ids": "",
        }
        
        return base64.b64encode(json.dumps(device_info).encode()).decode()
    
    def generate_fvideo_id(self):
        """生成fvideo-id"""
        timestamp = str(int(time.time() * 1000))
        return hashlib.md5(timestamp.encode()).hexdigest()
    
    def generate_fvideo_token(self):
        """生成fvideo-token"""
        timestamp = str(int(time.time() * 1000))
        token_data = f"token_{timestamp}_{self.generate_uuid()}"
        return base64.b64encode(hashlib.sha256(token_data.encode()).digest()).decode()

    def get_announcements_id(self, catalog_id='161', page_no='1', page_size='10'):
        """获取公告列表"""
        self.log("INFO", "正在获取公告列表...")
        
        # 构建请求参数
        params = {
            'type': '1',
            'pageNo': page_no,
            'pageSize': page_size,
            'catalogId': catalog_id,
        }
        
        # 构建请求头
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'bnc-level': '0',
            'bnc-location': 'CN',
            'bnc-time-zone': 'Asia/Hong_Kong',
            'bnc-uuid': self.generate_uuid(),
            'cache-control': 'no-cache',
            'clienttype': 'web',
            'content-type': 'application/json',
            'csrftoken': self.generate_csrf_token(),
            'device-info': self.generate_device_info(),
            'fvideo-id': self.generate_fvideo_id(),
            'fvideo-token': self.generate_fvideo_token(),
            'lang': 'zh-CN',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': f'{self.base_url}/zh-CN/support/announcement/list/{catalog_id}',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-host': 'www.binance.com',
            'x-passthrough-token': '',
            'x-trace-id': self.generate_uuid(),
            'x-ui-request-trace': self.generate_uuid(),
        }
        
        try:
            url = f'{self.base_url}/bapi/apex/v1/public/apex/cms/article/list/query'
            response = self.make_request(url, params=params, headers=headers, timeout=30)
            
            if response and response.status_code == 200:
                data = response.json()
                if 'data' in data and 'catalogs' in data['data'] and len(data['data']['catalogs']) > 0:
                    announcements = data['data']['catalogs'][0]["articles"]
                    self.log("INFO", f"成功获取 {len(announcements)} 条公告")
                    return announcements
                else:
                    self.log("ERROR", "响应数据格式异常")
                    self.log("ERROR", "响应内容:", data)
                    return []
            else:
                self.log("ERROR", f"请求失败，状态码: {response.status_code}")
                self.log("ERROR", "响应内容:", response.text)
                return []
                
        except Exception as e:
            self.log("ERROR", f"请求异常: {traceback.format_exc()}")
            return []
    
    async def parse_announcements_from_page(self):
        """从页面直接解析公告信息"""
        try:
            # 等待公告列表加载
            await self.page.wait_for_selector('.css-1wr4jig', timeout=10000)
            
            # 获取公告元素
            announcement_elements = await self.page.query_selector_all('.css-1wr4jig')
            
            announcements = []
            for element in announcement_elements[:10]:  # 只获取前10条
                try:
                    title = await element.query_selector('.css-1wr4jig')
                    if title:
                        title_text = await title.inner_text()
                        link_element = await element.query_selector('a')
                        if link_element:
                            href = await link_element.get_attribute('href')
                            article_id = href.split('/')[-1] if href else None
                            
                            announcements.append({
                                'title': title_text.strip(),
                                'id': article_id,
                                'url': href
                            })
                except:
                    continue
            
            self.log("INFO", f"从页面解析到 {len(announcements)} 条公告")
            return announcements
            
        except Exception as e:
            self.log("ERROR", f"页面解析失败: {traceback.format_exc()}")
            return []
    

    async def get_announcement_detail(self, article_id):
        """获取公告详情"""
        try:
            # 访问公告详情页
            detail_url = f'{self.base_url}/zh-CN/support/announcement/detail/{article_id}'
            self.log("INFO", f"访问URL: {detail_url}")
            
            await self.page.goto(detail_url)
            await self.random_delay(2, 4)
            
            # 等待页面加载
            await self.page.wait_for_load_state('networkidle')
            
            # 模拟人类行为
            await self.simulate_human_behavior()
            
            # 获取页面内容
            content = await self.page.content()
            
            # 尝试获取公告标题
            try:
                title_element = await self.page.query_selector('h1, .css-1wr4jig')
                if title_element:
                    title = await title_element.inner_text()
            except:
                pass
            
            # 提取纯文字内容
            text_content = self.parse_announcement_content(content)
            

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
            delisting_announcements = self.get_announcements_id()
            listing_announcements = self.get_announcements_id(catalog_id='48')
            announcements = delisting_announcements + listing_announcements
            if not announcements:
                self.log("ERROR", "未获取到公告", console=True)
                return
            
            # Counter for processed announcements in debug mode
            processed_count = 0
            
            for i, announcement in enumerate(announcements):
                try:
                    article_id = announcement.get('code')
                    json_filepath = os.path.join(self.output_dir, f"binance_{article_id}.json")
                    title = announcement.get('title', 'N/A')
                    release_time = int(announcement.get('releaseDate', 'N/A'))
                    release_time_str = pd.to_datetime(release_time, unit='ms', utc=True).tz_convert('Asia/Hong_Kong').strftime('%Y-%m-%d %H:%M:%S')
                    if release_time_str < (pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)).strftime('%Y-%m-%d %H:%M:%S'):
                        self.log("INFO", f"公告 {title} 发布时间 {release_time_str} 小于 {pd.Timestamp.now(tz='Asia/Hong_Kong') - pd.Timedelta(days=self.offset_days)}，跳过", console=True)
                        with open(json_filepath, 'w', encoding='utf-8') as f:
                            json.dump({'release_time': release_time_str, 'text': "", 'url': f"https://www.binance.com/zh-CN/support/announcement/detail/{article_id}", 'title': title,"exchange": "binance"}, f, ensure_ascii=False, indent=4)
                        continue

                    if not article_id:
                        continue
                        
                    self.log("INFO", f"处理公告 {i+1}/{len(announcements)}: {title}", console=True)
                    
                    # 检查文件是否已存在
                    # text_filepath = os.path.join(self.output_dir, f"binance_{article_id}.txt")
                    if os.path.exists(json_filepath):
                        self.log("INFO", f"公告详情已存在，跳过", console=True)
                        continue
                    
                    # 获取公告详情
                    detail_result = await self.get_announcement_detail(article_id)
                    if not detail_result:
                        self.log("ERROR", "获取详情失败", console=True)
                        continue
                    
                    text_content = detail_result['text']
                    if not text_content.strip():
                        self.log("ERROR", "文本内容为空", console=True)
                        continue
                    # analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
                    analysis_result = self.analyzer.analyze_announcement(text_content)
                    
                    # 显示分析结果
                    self.analyzer.print_analysis_result(analysis_result)
                    
                    # 保存分析结果
                    self.analyzer.save_analysis_result(analysis_result, json_filepath, {
                            'title': title,
                            'exchange': 'binance',
                            'url': f"https://www.binance.com/zh-CN/support/announcement/detail/{article_id}",
                            "release_time": release_time_str,
                            "content": text_content
                        })
                    
                    processed_count += 1
                    
                    await self.random_delay(2, 5)
                    
                except Exception as e:
                    self.log("ERROR", f"处理公告 {title} 时出错: {traceback.format_exc()}")
                    continue
            
            self.log("INFO", f"\n{self.exchange_name} 抓取完成，共处理 {processed_count} 个公告", console=True)
            
        except Exception as e:
            self.log("ERROR", f"程序执行出错: {traceback.format_exc()}", console=True)
        finally:
            await self.cleanup_browser()

async def main():
    """主函数，创建爬虫实例并运行"""
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = BinanceScraper(analyzer, debug=True, max_size=5)  # Debug mode for testing
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
