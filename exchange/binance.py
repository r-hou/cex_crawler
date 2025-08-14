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
from deepseek_analyzer import DeepSeekAnalyzer
import traceback
import os

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BinanceScraper:
    def __init__(self, analyzer: DeepSeekAnalyzer):
        self.base_url = "https://www.binance.com"
        self.browser = None
        self.context = None
        self.page = None
        self.analyzer = analyzer
        
    async def init_browser(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        
        # 启动浏览器，使用无头模式
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # 设置为True为无头模式
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # 禁用图片加载，提高速度
            ]
        )
        
        # 创建上下文
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Hong_Kong',
            extra_http_headers={
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
        )
        
        # 创建页面
        self.page = await self.context.new_page()
        
        # 设置页面属性，避免被检测
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en'],
            });
            
            window.chrome = {
                runtime: {},
            };
        """)
        
        print("浏览器初始化完成")
    
    async def random_delay(self, min_delay=1, max_delay=3):
        """随机延迟，模拟人类行为"""
        delay = random.uniform(min_delay, max_delay)
        print(f"等待 {delay:.2f} 秒...")
        await asyncio.sleep(delay)
    
    async def simulate_human_behavior(self):
        """模拟人类行为"""
        # 随机滚动
        await self.page.mouse.wheel(0, random.randint(100, 500))
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # 随机移动鼠标
        await self.page.mouse.move(
            random.randint(100, 800), 
            random.randint(100, 600)
        )
        await asyncio.sleep(random.uniform(0.3, 0.8))
    
    def generate_uuid(self):
        """生成UUID"""
        import uuid
        return str(uuid.uuid4())
    
    def generate_csrf_token(self):
        """生成CSRF token"""
        import hashlib
        import time
        timestamp = str(int(time.time() * 1000))
        return hashlib.md5(timestamp.encode()).hexdigest()
    
    def generate_device_info(self):
        """生成设备信息"""
        import base64
        import json
        
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
        import hashlib
        import time
        timestamp = str(int(time.time() * 1000))
        return hashlib.md5(timestamp.encode()).hexdigest()
    
    def generate_fvideo_token(self):
        """生成fvideo-token"""
        import base64
        import hashlib
        import time
        
        timestamp = str(int(time.time() * 1000))
        token_data = f"token_{timestamp}_{self.generate_uuid()}"
        return base64.b64encode(hashlib.sha256(token_data.encode()).digest()).decode()

    def get_announcements_id(self, catalog_id='161', page_no='1', page_size='10'):
        """获取公告列表"""
        print("正在获取公告列表...")
        
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
            response = requests.get(
                f'{self.base_url}/bapi/apex/v1/public/apex/cms/article/list/query',
                params=params,
                headers=headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'catalogs' in data['data'] and len(data['data']['catalogs']) > 0:
                    announcements = data['data']['catalogs'][0]["articles"]
                    print(f"成功获取 {len(announcements)} 条公告")
                    return announcements
                else:
                    print("响应数据格式异常")
                    print("响应内容:", data)
                    return []
            else:
                print(f"请求失败，状态码: {response.status_code}")
                print("响应内容:", response.text)
                return []
                
        except Exception as e:
            print(f"请求异常: {e}")
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
            
            print(f"从页面解析到 {len(announcements)} 条公告")
            return announcements
            
        except Exception as e:
            print(f"页面解析失败: {e}")
            return []
    
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

    async def get_announcement_detail(self, article_id):
        """获取公告详情"""
        print(f"正在获取公告详情: {article_id}")
        
        try:
            # 访问公告详情页
            detail_url = f'{self.base_url}/zh-CN/support/announcement/detail/{article_id}'
            print(f"访问URL: {detail_url}")
            
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
                    print(f"公告标题: {title}")
            except:
                pass
            
            # 提取纯文字内容
            text_content = self.extract_text_from_html(content)
            
            print("成功获取公告详情")
            return {
                'html': content,
                'text': text_content
            }
            
        except Exception as e:
            print(f"获取公告详情失败: {e}")
            return None
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("浏览器已关闭")
    
    async def run_scraping(self):
        """运行爬虫主流程"""
        try:
            # 初始化浏览器
            await self.init_browser()
            
            # 获取公告列表
            announcements = self.get_announcements_id()
            
            if announcements:
                print("\n=== 公告列表 ===")
                for i, announcement in enumerate(announcements):  # 只显示前3条
                    print(f"{i}. ID: {announcement.get('id', 'N/A')}")
                    print(f"   标题: {announcement.get('title', 'N/A')}")
                    print(f"   URL: https://www.binance.com/zh-CN/support/announcement/detail/{announcement.get('code', 'N/A')}")
                    print()
                
                # 获取第一条公告的详情
                for article in announcements:
                    article_id = article.get('code')
                    if article_id:
                        text_file_name = f'announcements_text/binance_{article_id}.txt'
                        json_file_name = f'announcements_json/binance_{article_id}.json'
                        if os.path.exists(text_file_name) and os.path.exists(json_file_name):
                            print(f"公告详情已存在: {text_file_name}")
                            continue
                        print("=== 获取公告详情 ===")
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
                                self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'binance'})
                                
                            except Exception as e:
                                print(f"DeepSeek分析失败: {traceback.format_exc()}")
                        else:
                            print("获取详情失败")
            
            print("\n程序执行完成")
            
        except Exception as e:
            print(f"程序执行出错: {e}")
        
        finally:
            # 关闭浏览器
            await self.close()

async def main():
    """主函数，创建爬虫实例并运行"""
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = BinanceScraper(analyzer)
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
