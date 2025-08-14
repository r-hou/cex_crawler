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

class BitgetScraper:
    def __init__(self, analyzer: DeepSeekAnalyzer):
        self.base_url = "https://www.bitget.com"
        self.browser = None
        self.context = None
        self.page = None
        self.analyzer = analyzer
        self.build_id = None
        
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
    
    async def get_announcement_detail(self, article_id):
        """获取公告详情"""
        print(f"正在获取公告详情: {article_id}")
        
        try:
            # 方法1: 使用page.evaluate()发送POST请求
            api_url = f"https://www.bitget.com/support/_next/data/{self.build_id}/en/support/articles/{article_id}.json?contentId={article_id}"
            content = await self.get_page_content(api_url, 'load')
            json_data = self.get_json_from_html(content)


            text_content = json_data['pageProps']['details']['title']  + "\n" + self.extract_text_from_html(json_data['pageProps']['details']['content']) 

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
                article_id = article.get('simpleResult').get('contentId')
                text_file_name = f'announcements_text/bitget_{article_id}.txt'
                json_file_name = f'announcements_json/bitget_{article_id}.json'
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
    scraper = BitgetScraper(analyzer)
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
