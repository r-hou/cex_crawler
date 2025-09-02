from openai import OpenAI
import json
import re
from datetime import datetime
import os
from typing import Dict, List, Optional
import traceback
from utils import file_logger, console_logger

class DeepSeekAnalyzer:
    def __init__(self, api_key: str = None):
        """
        初始化OpenAI分析器
        
        Args:
            api_key: OpenAI API密钥，如果不提供则从环境变量获取
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("请提供OpenAI API密钥或设置OPENAI_API_KEY环境变量")
        
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
        self.model = "deepseek-chat"

        
        # 分析提示词
        self.analysis_prompt = """
你是一个专业的加密货币交易所公告分析专家。请分析以下公告内容, 公告内容可能是中文，英语或者韩语，提取出所有关于数字货币上架和下架的信息。

请严格按照以下JSON格式输出，只包含上架和下架信息：

{{
    "listings": [
        {{
            "symbol": "交易对符号",
            "action": "上架",
            "type": "现货/合约",
            "time": "具体日期"
        }}
    ],
    "delistings": [
        {{
            "symbol": "交易对符号", 
            "action": "下架",
            "type": "现货/合约",
            "time": "具体日期"
        }}
    ]
}}

注意事项：
1. 只提取上架/下架信息
2. 时间格式要具体，格式是"YYYY-MM-DD"，不需要时区信息, 不能包含汉字或者韩语，必须输出时间，如果时间格式是"YYYY年MM月DD日"，则转换为"YYYY-MM-DD", 如果时间是YYYY年M月D日(比如2025年7月6日)，则转换为"2025-07-06"
3. 交易对符号要准确，如"BTC/USDT"
4. type字段必须填写"现货"或"合约"，根据公告内容判断
5. 如果没有相关信息，返回空数组
6. 只输出JSON格式，不要其他文字
7. **宽松识别**：只要涉及开始任何形式的交易都算作上架

公告内容：
{content}
"""

    def analyze_announcement(self, text_content: str) -> Dict:
        """
        分析公告文字内容，提取上架/下架信息
        
        Args:
            text_content: 公告的纯文字内容
            
        Returns:
            包含上架/下架信息的字典
        """
        try:
            file_logger.info("正在使用DeepSeek分析公告内容...")
            
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的加密货币公告分析专家。"},
                    {"role": "user", "content": self.analysis_prompt.format(content=text_content)}
                ],
                temperature=0.1,  # 低温度确保输出一致性
                max_tokens=1000
            )
            
            # 提取回复内容
            ai_response = response.choices[0].message.content.strip()
            
            # 尝试解析JSON
            try:
                result = json.loads(ai_response)
                return self._validate_and_clean_result(result)
            except json.JSONDecodeError:
                file_logger.info("OpenAI返回的不是有效JSON，尝试修复...")
                return self._fix_json_response(ai_response)
                
        except Exception as e:
            file_logger.info(f"OpenAI API调用失败: {traceback.format_exc()}")
            console_logger.info(f"OpenAI API调用失败: {traceback.format_exc()}")
            return self._fallback_analysis(text_content)
    
    def _validate_and_clean_result(self, result: Dict) -> Dict:
        """验证和清理结果"""
        # 确保结果包含必要的字段
        if 'listings' not in result:
            result['listings'] = []
        if 'delistings' not in result:
            result['delistings'] = []
            
        # 验证每个条目
        for listing in result['listings']:
            if not all(key in listing for key in ['symbol', 'action', 'type', 'time']):
                # 设置默认值
                if 'action' not in listing:
                    listing['action'] = '上架'
                if 'type' not in listing:
                    listing['type'] = '现货'  # 默认现货
                if 'time' not in listing:
                    listing['time'] = '时间未明确'
                
        for delisting in result['delistings']:
            if not all(key in delisting for key in ['symbol', 'action', 'type', 'time']):
                # 设置默认值
                if 'action' not in delisting:
                    delisting['action'] = '下架'
                if 'type' not in delisting:
                    delisting['type'] = '现货'  # 默认现货
                if 'time' not in delisting:
                    delisting['time'] = '时间未明确'
                
        return result
    
    def _fix_json_response(self, response: str) -> Dict:
        """修复OpenAI返回的不完整JSON"""
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                fixed_json = json_match.group()
                return json.loads(fixed_json)
        except:
            pass
            
        # 如果无法修复，返回空结果
        return {"listings": [], "delistings": []}
    
    def _fallback_analysis(self, text_content: str) -> Dict:
        """备用分析方法（基于关键词匹配）"""
        file_logger.info("使用备用分析方法...")
        
        result = {"listings": [], "delistings": []}
        
        # 简单的关键词匹配
        text_lower = text_content.lower()
        
        # 查找上架相关词汇
        listing_keywords = ['上架', '上线', '新增', '开放交易', '开始交易', 'listing']
        delisting_keywords = ['下架', '下线', '停止交易', '终止交易', 'delisting', 'removal']
        
        # 查找交易对符号（简单的正则表达式）
        symbol_pattern = r'[A-Z]{2,10}/[A-Z]{2,10}|[A-Z]{2,10}-[A-Z]{2,10}'
        symbols = re.findall(symbol_pattern, text_content.upper())
        
        # 查找时间信息（简化为日期格式）
        time_pattern = r'\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2}'
        times = re.findall(time_pattern, text_content)
        
        # 判断是现货还是合约
        def determine_type(text):
            text_lower = text.lower()
            if any(word in text_lower for word in ['合约', '永续', 'futures', 'perpetual']):
                return '合约'
            elif any(word in text_lower for word in ['现货', 'spot']):
                return '现货'
            else:
                return '现货'  # 默认现货
        
        # 根据关键词判断是上架还是下架
        if any(keyword in text_lower for keyword in listing_keywords):
            for symbol in symbols[:3]:  # 最多取3个
                result['listings'].append({
                    'symbol': symbol,
                    'action': '上架',
                    'type': determine_type(text_content),
                    'time': times[0] if times else '时间未明确'
                })
        
        if any(keyword in text_lower for keyword in delisting_keywords):
            for symbol in symbols[:3]:  # 最多取3个
                result['delistings'].append({
                    'symbol': symbol,
                    'action': '下架',
                    'type': determine_type(text_content),
                    'time': times[0] if times else '时间未明确'
                })
        
        return result
    
    def print_analysis_result(self, result: Dict):
        """打印分析结果"""
        file_logger.info("\n" + "="*60)
        file_logger.info("📊 公告分析结果")
        file_logger.info("="*60)
        
        # 上架信息
        if result['listings']:
            file_logger.info("\n🟢 上架信息:")
            for listing in result['listings']:
                file_logger.info(f"   • {listing['symbol']} - {listing['action']} - {listing['type']} - {listing['time']}")
        else:
            file_logger.info("\n🟢 上架信息: 无")
        
        # 下架信息
        if result['delistings']:
            file_logger.info("\n🔴 下架信息:")
            for delisting in result['delistings']:
                file_logger.info(f"   • {delisting['symbol']} - {delisting['action']} - {delisting['type']} - {delisting['time']}")
        else:
            file_logger.info("\n🔴 下架信息: 无")
        
        file_logger.info("="*60)
    
    def save_analysis_result(self, result: Dict, filename: str = None, updates = {}):
        """保存分析结果到文件"""    
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_result_{timestamp}.json"
        
        try:
            # 合并上架和下架信息到一个列表
            all_results = result.get("listings", []) + result.get("delistings", [])
            if updates:
                all_results = [ {**item, **updates} for item in all_results ]
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
            file_logger.info(f"分析结果已保存到: {filename}")
            console_logger.info(f"分析结果已保存到: {filename}")
        except Exception as e:
            file_logger.info(f"保存结果失败: {e}")
            console_logger.info(f"保存结果失败: {e}")

def main():
    """测试函数"""
    # 示例用法
    try:
        analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")
        
        # 示例公告内容
        sample_text = """Bitget pre-market trading: World Liberty Financial (WLFI) is set to launch soon
We're thrilled to announce that Bitget will launch World Liberty Financial (WLFI) in pre-market trading. Users can trade WLFI in advance, before it becomes available for spot trading. Details are as follows:
Start time: 23 August, 2025, 14:00 (UTC)
End time: TBD
Spot Trading time: TBD
Delivery Start time: TBD
Delivery End time: TBD
Pre-market trading link: WLFI/USDT
Bitget Pre-Market Introduction
Delivery method: Coin settlement, USDT settlement
Coin settlement
Starting from the project's delivery start time, the system will periodically execute multiple deliveries for orders under the Coin Settlement mode. Sell orders with sufficient spot balances will be filled with corresponding buy orders. If there are insufficient project tokens or if sellers voluntarily choose to default, compensation with security deposits will not be triggered immediately. At the project's delivery end time, the system will either d..."""
        
        print("示例分析:")
        result = analyzer.analyze_announcement(sample_text)
        analyzer.print_analysis_result(result)
        
    except Exception as e:
        print(f"错误: {e}")
        print("请确保设置了OPENAI_API_KEY环境变量")

if __name__ == "__main__":
    main()
