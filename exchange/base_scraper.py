import asyncio
import time
import random
import json
import os
import hashlib
from typing import Dict, List, Optional, Any
from pprint import pprint
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import urllib3
import requests
from bs4 import BeautifulSoup
from deepseek_analyzer import DeepSeekAnalyzer
import traceback

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BaseScraper:
    """Base class for all exchange scrapers to eliminate code duplication"""
    
    def __init__(self, exchange_name: str, base_url: str, analyzer: DeepSeekAnalyzer = None, debug: bool = False, max_size: int = 10):
        """
        Initialize base scraper
        
        Args:
            exchange_name: Name of the exchange (e.g., 'binance', 'bingx')
            base_url: Base URL of the exchange
            analyzer: DeepSeekAnalyzer instance
            debug: Debug mode flag
            max_size: Maximum number of announcements to process in debug mode
        """
        self.exchange_name = exchange_name
        self.base_url = base_url
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.analyzer = analyzer
        self.debug = debug
        self.max_size = max_size
        self.playwright = None
        
        # Ensure output directory exists
        self.output_dir = f"output/{exchange_name}"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Common headers for requests
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': base_url,
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
        """Initialize Playwright browser with common settings"""
        self.playwright = await async_playwright().start()
        
        # Common browser launch arguments
        browser_args = [
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
            '--disable-images',  # Disable image loading for speed
        ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=browser_args
        )
        
        # Create browser context with common settings
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
        
        # Create page
        self.page = await self.context.new_page()
        
        # Add anti-detection script
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
        
        print(f"{self.exchange_name} 浏览器初始化完成")
    
    async def cleanup_browser(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            print(f"{self.exchange_name} 浏览器资源清理完成")
        except Exception as e:
            print(f"{self.exchange_name} 清理浏览器资源时出错: {e}")
    
    async def random_delay(self, min_delay: float = 1, max_delay: float = 3):
        """Random delay to simulate human behavior"""
        delay = random.uniform(min_delay, max_delay)
        print(f"等待 {delay:.2f} 秒...")
        await asyncio.sleep(delay)
    
    async def simulate_human_behavior(self):
        """Simulate human behavior on the page"""
        try:
            if self.page:
                # Random mouse movement
                await self.page.mouse.move(
                    random.randint(100, 800),
                    random.randint(100, 600)
                )
                await self.random_delay(0.5, 1.5)
                
                # Random scroll
                await self.page.evaluate(f"window.scrollBy(0, {random.randint(100, 300)})")
                await self.random_delay(0.5, 1.0)
        except Exception as e:
            print(f"模拟人类行为时出错: {e}")
    
    def generate_file_id(self, content: str) -> str:
        """Generate unique file ID based on content hash"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def save_json_file(self, data: List[Dict], file_id: str) -> str:
        """Save JSON data to file"""
        filename = f"{self.exchange_name}_{file_id}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"JSON文件已保存: {filepath}")
            return filepath
        except Exception as e:
            print(f"保存JSON文件失败: {e}")
            return ""
    
    def save_text_file(self, content: str, file_id: str) -> str:
        """Save text content to file"""
        filename = f"{self.exchange_name}_{file_id}.txt"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"文本文件已保存: {filepath}")
            return filepath
        except Exception as e:
            print(f"保存文本文件失败: {e}")
            return ""
    
    def analyze_and_save_announcement(self, text_content: str, updates: Dict = None) -> Optional[str]:
        """Analyze announcement text and save results"""
        if not self.analyzer or not text_content.strip():
            return None
        
        try:
            # Generate file ID from content
            file_id = self.generate_file_id(text_content)
            
            # Save text file
            text_filepath = self.save_text_file(text_content, file_id)
            
            # Analyze with AI
            result = self.analyzer.analyze_announcement(text_content)
            self.analyzer.print_analysis_result(result)
            
            # Add exchange information and any additional updates
            base_updates = {"exchange": self.exchange_name}
            if updates:
                base_updates.update(updates)
            
            # Save analysis results
            json_filepath = self.save_json_file(
                result.get("listings", []) + result.get("delistings", []), 
                file_id
            )
            
            # Update saved results with additional info
            if json_filepath and base_updates:
                self.analyzer.save_analysis_result(result, json_filepath, base_updates)
            
            return json_filepath
            
        except Exception as e:
            print(f"分析和保存公告时出错: {e}")
            traceback.print_exc()
            return None
    
    def make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with common headers and error handling"""
        try:
            headers = kwargs.pop('headers', {})
            final_headers = {**self.headers, **headers}
            
            response = requests.get(url, headers=final_headers, verify=False, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"HTTP请求失败 {url}: {e}")
            return None
    
    def limit_results_for_debug(self, items: List[Any]) -> List[Any]:
        """Limit results if in debug mode"""
        if self.debug and len(items) > self.max_size:
            print(f"Debug模式: 限制处理 {self.max_size} 个项目 (总共 {len(items)} 个)")
            return items[:self.max_size]
        return items
    
    # Abstract methods that subclasses should implement
    async def run_scraping(self):
        """Main scraping method - should be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement run_scraping method")
    
    def get_announcements_urls(self) -> List[str]:
        """Get list of announcement URLs - should be implemented by subclasses if needed"""
        return []
    
    def parse_announcement_content(self, content: str) -> str:
        """Parse and clean announcement content - can be overridden by subclasses"""
        # Basic cleaning - subclasses can override for exchange-specific parsing
        if isinstance(content, str):
            soup = BeautifulSoup(content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            # Get text and clean it
            text = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return '\n'.join(chunk for chunk in chunks if chunk)
        return content