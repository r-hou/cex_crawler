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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepseek_analyzer import DeepSeekAnalyzer
import traceback

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BithumbScraper:
    def __init__(self, analyzer: DeepSeekAnalyzer):
        self.base_url = "https://www.bithumb.com"
        self.browser = None
        self.context = None
        self.page = None
        self.analyzer = analyzer
        self.build_id = None
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://feed.bithumb.com/',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'x-nextjs-data': '1',
        }
        
    async def init_browser(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        
        # 启动浏览器，使用无头模式
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # 临时设置为False以便调试Cloudflare
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
                '--disable-images',
                '--disable-javascript-harmony-shipping',
                '--disable-site-isolation-trials',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-domain-reliability',
                '--disable-component-extensions-with-background-pages',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--no-default-browser-check',
                '--no-first-run',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-client-side-phishing-detection',
                '--disable-default-apps',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-sync',
                '--disable-web-resources',
                '--metrics-recording-only',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--enable-automation',
                '--password-store=basic',
                '--use-mock-keychain',
            ]
        )
        
        # 创建上下文
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Hong_Kong',
            extra_http_headers={
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'priority': 'u=1, i',
                'referer': 'https://feed.bithumb.com/',
                'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
                'x-nextjs-data': '1',
            }
        )
        
        # 创建页面
        self.page = await self.context.new_page()
        
        # 设置页面属性，避免被检测
        await self.page.add_init_script("""
            // 隐藏webdriver属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 模拟插件
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        name: 'Chrome PDF Plugin',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format'
                    },
                    {
                        name: 'Chrome PDF Viewer',
                        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                        description: ''
                    },
                    {
                        name: 'Native Client',
                        filename: 'internal-nacl-plugin',
                        description: ''
                    }
                ],
            });
            
            // 模拟语言
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            });
            
            // 模拟chrome对象
            window.chrome = {
                runtime: {
                    onConnect: undefined,
                    onMessage: undefined,
                    sendMessage: undefined,
                    connect: undefined,
                    id: undefined
                },
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 隐藏自动化相关属性
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // 模拟permissions API
            if (!navigator.permissions) {
                navigator.permissions = {
                    query: function() {
                        return Promise.resolve({ state: 'granted' });
                    }
                };
            }
            
            // 模拟webGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel(R) Iris(TM) Graphics 6100';
                }
                return getParameter.apply(this, arguments);
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

    async def handle_cloudflare_protection(self, url, max_retries=3):
        """处理Cloudflare保护"""
        for attempt in range(max_retries):
            try:
                print(f"尝试访问 {url} (第 {attempt + 1} 次)")
                
                # 导航到页面
                await self.page.goto(url, wait_until='domcontentloaded')
                await self.random_delay(3, 5)
                
                # 检查是否遇到Cloudflare保护页面
                page_content = await self.page.content()
                if "Attention Required!" in page_content or "Cloudflare" in page_content:
                    print("检测到Cloudflare保护页面，等待处理...")
                    
                    # 等待Cloudflare检查完成
                    try:
                        # 等待页面加载完成或超时
                        await self.page.wait_for_load_state('networkidle', timeout=30000)
                        await self.random_delay(5, 10)
                        
                        # 检查是否还有Cloudflare页面
                        current_content = await self.page.content()
                        if "Attention Required!" not in current_content and "Cloudflare" not in current_content:
                            print("Cloudflare检查完成，页面已正常加载")
                            return await self.page.content()
                        else:
                            print("Cloudflare检查仍在进行，继续等待...")
                            await self.random_delay(10, 15)
                            
                    except Exception as e:
                        print(f"等待Cloudflare检查时出错: {e}")
                        await self.random_delay(5, 8)
                else:
                    print("页面正常加载，未遇到Cloudflare保护")
                    return await self.page.content()
                    
            except Exception as e:
                print(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt < max_retries - 1:
                    await self.random_delay(5, 10)
                else:
                    raise e
        
        raise Exception("无法绕过Cloudflare保护")

    
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

        content = await self.get_page_content('https://feed.bithumb.com/notice', 'load')
        json_data = self.extract_json_from_script(content)
        self.build_id = json_data['buildId']
        delisting_url = f'https://feed.bithumb.com/notice?category=6&page=1'
        listing_url = f'https://feed.bithumb.com/notice?category=1&page=1'
        listing_content = await self.get_page_content(listing_url, 'load')
        with open('listing_content.html', 'w') as f:
            f.write(listing_content)
        listing_json_data = self.get_json_from_html(listing_content)
        pprint(listing_json_data)
        announcements_listing = listing_json_data['props']['pageProps']['noticeList']
        announcements_listing = [ i for i in announcements_listing if i['categoryName1'] in ["안내", "거래지원종료"]]
        
        delisting_content = await self.get_page_content(delisting_url, 'load')
        delisting_json_data = self.get_json_from_html(delisting_content)
        announcements_delisting = delisting_json_data['props']['pageProps']['noticeList']
        announcements_delisting = [ i for i in announcements_delisting if i['categoryName1'] in ["안내", "거래지원종료"]]
        pprint(announcements_listing)
        pprint(announcements_delisting)
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
                    print(f"解析 __NEXT_DATA__ JSON失败: {e}")
            
            
            if not json_data:
                print("未找到script标签中的JSON数据")
            
            return json_data
            
        except Exception as e:
            print(f"提取script标签JSON数据失败: {e}")
            return {}
        
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
        try:
            # 使用Cloudflare保护处理方法
            content = await self.handle_cloudflare_protection(url)
            return content
        except Exception as e:
            print(f"获取页面内容失败: {e}")
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


            text_content = json_data['props']['pageProps']['data']['title']  + "\n" + self.extract_text_from_html(json_data['props']['pageProps']['data']['content']) 

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
            
            # 获取公告分类数据
            announcements = await self.get_announcements_id()
            for i, article in enumerate(announcements):
                article_id = article.get('id')
                text_file_name = f'announcements_text/bithumb_{article_id}.txt'
                json_file_name = f'announcements_json/bithumb_{article_id}.json'
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
                            
                        except Exception as e:
                            print(f"DeepSeek分析失败: {traceback.format_exc()}")
                    else:
                        print("获取详情失败")
                        exit()
            
        except Exception as e:
            print(f"程序执行出错: {traceback.format_exc()}")
        
        finally:
            # 关闭浏览器
            await self.close()

async def main():
    """主函数，创建爬虫实例并运行"""
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
    scraper = BithumbScraper(analyzer)
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
