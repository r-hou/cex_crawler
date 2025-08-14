import pandas as pd
import ccxt
import time
import pprint
import json
import traceback

class OkxScraper:
    def __init__(self):
        self.exchange = ccxt.okx()

    def run_scraping(self):
        try:
            coin_infos = self.exchange.fetch_markets()
            res = []
            for coin_info in coin_infos:
                if coin_info['type'] in ['option', 'future']:
                    continue
                list_time = coin_info['info']['listTime']
                list_time = pd.to_datetime(list_time, unit='ms')

                # if list time is within 7 days, add to res
                if (list_time >= pd.Timestamp.now() - pd.Timedelta(days=7)) and (coin_info['quote'] != 'USD'):
                    pprint.pprint(coin_info, indent=4)
                    res.append({
                            "symbol": coin_info['symbol'],
                            "action": "上架",
                            "type": "现货" if coin_info['type'] == 'spot' else "合约",
                            "time": list_time.strftime("%Y-%m-%d"),
                            "exchange": "okx"
                            })
                if (coin_info['info']['expTime'] != '') and (coin_info['quote'] != 'USD'):
                    exp_time = int(coin_info['info']['expTime'])
                    exp_time = pd.to_datetime(exp_time, unit='ms')
                    res.append({
                            "symbol": coin_info['symbol'],
                            "action": "下架",
                            "type": "现货" if coin_info['type'] == 'spot' else "合约",
                            "time": exp_time.strftime("%Y-%m-%d"),
                            "exchange": "okx"
                            })
            print("=== okx 上下币信息 ===")

            delistings = [item for item in res if item['action'] == '下架']
            listings = [item for item in res if item['action'] == '上架']
            
            # 上架信息
            if listings:
                print("\n🟢 上架信息:")
                for listing in listings:
                    print(f"   • {listing['symbol']} - {listing['action']} - {listing['type']} - {listing['time']}")
            else:
                print("\n🟢 上架信息: 无")

            if delistings:
                print("\n🔴 下架信息:")
                for delisting in delistings:
                    print(f"   • {delisting['symbol']} - {delisting['action']} - {delisting['type']} - {delisting['time']}")
            else:
                print("\n🔴 下架信息: 无")
            print("okx 上下币信息保存到 announcements_json/okx.json")
            print("="*60)

            with open("announcements_json/okx.json", "w") as f:
                json.dump(res, f, ensure_ascii=False, indent=2)
            return res
        except Exception as e:
            print("okx 上下币信息获取失败, 报错:")
            print(traceback.format_exc())
            return []

if __name__ == "__main__":
    scraper = OkxScraper()
    scraper.run_scraping()
