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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepseek_analyzer import DeepSeekAnalyzer
import traceback

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BlofinScraper:
    def __init__(self, analyzer: DeepSeekAnalyzer):
        self.base_url = "https://www.blofin.com"
        self.browser = None
        self.context = None
        self.page = None
        self.analyzer = analyzer
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://support.blofin.com/hc/en-us',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        }
        
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


        
    async def get_announcements_id(self, catalog_id='161', page_no='1', page_size='10'):
        """获取公告列表"""
        content = await self.get_page_content('https://support.blofin.com/hc/en-us', 'load')


        
        soup = BeautifulSoup(content, 'html.parser')
        
        # 查找所有class为promoted-articles-item的li标签
        promoted_items = soup.find_all('a')

        
        announcement_url = ""
        for i, a_tag in enumerate(promoted_items):
            href = a_tag.get('href')
            text = a_tag.get_text(strip=True)
            if "announcement" in text.lower():
                announcement_url = f"https://support.blofin.com/{href}" 
        
        if len(announcement_url) == 0:
            print("未找到blofin公告链接")
            exit()
        
        print(f"blofin公告链接: {announcement_url}")

        content = await self.get_page_content(announcement_url, 'load')
        
        announcements = []
        soup = BeautifulSoup(content, 'html.parser')
        section_tags = soup.find_all('section', class_='section')
        print(f"section_tags: {len(section_tags)}")
        for section_tag in section_tags:
            h2 = section_tag.find('h2', class_="section-tree-title")
            if not h2:
                continue
            section_text = h2.get_text(strip=True)
            if "list" in section_text.lower():
                a_tags = section_tag.find("ul", class_="article-list").find_all('a')
                for a_tag in a_tags:
                    href = a_tag.get('href')
                    if href:
                        announcement = {
                            'href': href,
                            'title': a_tag.get_text(strip=True),
                            "full_url": f"https://support.blofin.com/{href}"
                        }
                        announcements.append(announcement)
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
            article_body = soup.find("div", class_="article-content")
            
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
                full_url = article.get('full_url')
                article_id = md5(full_url.encode('utf-8')).hexdigest()
                text_file_name = f'announcements_text/blofin_{article_id}.txt'
                json_file_name = f'announcements_json/blofin_{article_id}.json'
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
                            self.analyzer.save_analysis_result(analysis_result, json_file_name, updates={'exchange': 'blofin'})
                            
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
    scraper = BlofinScraper(analyzer)
    await scraper.run_scraping()

if __name__ == "__main__":
    asyncio.run(main())
