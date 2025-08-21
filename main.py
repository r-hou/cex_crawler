import os
import asyncio
import glob
import json
import pandas as pd
from exchange.binance import BinanceScraper
from exchange.bingx import BingxScraper
from exchange.bitunix import BitunixScraper
from exchange.blofin import BlofinScraper
from exchange.bitget import BitgetScraper
from exchange.btcc import BtccScraper
from exchange.bybit import BybitScraper
from exchange.gate import GateScraper
from exchange.mexc import MexcScraper
from exchange.okx import OkxScraper
from exchange.lbank import LbankScraper
from exchange.weex import WeexScraper
from exchange.bithumb import BithumbScraper
from exchange.coinex import CoinexScraper
from exchange.upbit import UpbitScraper
from deepseek_analyzer import DeepSeekAnalyzer

# Configuration
DEBUG_MODE = True  # Set to True for debug mode
MAX_DEBUG_SIZE = 20  # Maximum announcements per exchange in debug mode


SPOT_CEX = ["binance", "bingx", "bitget", "bybit", "gate", "mexc", "lbank", 'upbit', 'bithumb', 'coinex']
FUTURES_CEX = ["binance", "bingx", "bitunix", "blofin", "bitget", "btcc", "bybit", "gate", "mexc", "okx", "lbank", "weex"]

def save_accoucements_to_csv():
    # Update to work with new file structure in output/*/
    files = glob.glob("output/*/*.json")
    announcements = []
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)
            # Update file path to point to corresponding text file
            text_file = file.replace(".json", ".txt")
            data = [{**{"file": text_file}, **i} for i in data]
            announcements += data
    df = pd.DataFrame(announcements)
    today = pd.to_datetime(pd.Timestamp.now(tz='Asia/Shanghai').strftime("%Y-%m-%d"))
    start_date = today - pd.Timedelta(days=7)
    df["comments"] = ""
    df = df[df["time"]!="待定"]
    df.loc[(df["time"].isna()) | (df["time"].str.len()<10), "comments"] = "待确定"
    df["time"] = df["time"].fillna(today.strftime("%Y-%m-%d"))
    df["time"] = df["time"].apply(lambda x: today.strftime("%Y-%m-%d") if (pd.isna(x) or x == "" or len(x) < 10) else x)
    df.to_csv("announcements.csv", index=False)
    df = df.drop(columns=["file"])
    # 转换时间列，确保没有时区信息
    df['time'] = pd.to_datetime(df['time'])
    # 过滤最近7天的数据
    df = df[df['time'] >= start_date]
    df["description"] = df.apply(lambda x: x["comments"] + x["action"] + " " + x["symbol"].replace("/USDT", "").replace("USDT", "")+"\n", axis=1)
    spot_df = df[(df["type"] == "现货") & df["exchange"].isin(SPOT_CEX)]
    spot_df = spot_df.groupby(["time", "exchange"]).agg({"description": " ".join})
    spot_df = spot_df.reset_index()
    spot_df = spot_df.pivot(index="time", columns="exchange", values="description")
    for exchange in SPOT_CEX:
        if not exchange in spot_df.columns:
            spot_df[exchange] = ""
    spot_df.to_csv("announcements_spot.csv", index=True)
    print("save_accoucements_to_csv spot done")
    futures_df = df[(df["type"] == "合约") & df["exchange"].isin(FUTURES_CEX)]
    futures_df = futures_df.groupby(["time", "exchange"]).agg({"description": " ".join})
    futures_df = futures_df.reset_index()
    futures_df = futures_df.pivot(index="time", columns="exchange", values="description")
    for exchange in FUTURES_CEX:
        if not exchange in futures_df.columns:
            futures_df[exchange] = ""
    futures_df.to_csv("announcements_futures.csv", index=True)
    print("save_accoucements_to_csv done")

async def crawl_announcements():
    # Ensure output directory exists
    if not os.path.exists("output"):
        os.makedirs("output", exist_ok=True)

    # Create analyzer
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")

    print(f"Debug mode: {DEBUG_MODE}")
    if DEBUG_MODE:
        print(f"Maximum announcements per exchange: {MAX_DEBUG_SIZE}")

    # Initialize scrapers with debug configuration
    scrapers = [
        BinanceScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        BingxScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        BitunixScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        BlofinScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        BitgetScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        BtccScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        BybitScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        GateScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        MexcScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        LbankScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        WeexScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        CoinexScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        UpbitScraper(analyzer, DEBUG_MODE, MAX_DEBUG_SIZE),
        OkxScraper(DEBUG_MODE, MAX_DEBUG_SIZE),  # OKX doesn't use analyzer
    ]

    # Run scrapers
    for scraper in scrapers:
        try:
            print(f"\n=== Starting {scraper.exchange_name} scraper ===")
            if hasattr(scraper, 'run_scraping') and asyncio.iscoroutinefunction(scraper.run_scraping):
                await scraper.run_scraping()
            else:
                scraper.run_scraping()
        except Exception as e:
            print(f"Error running {scraper.exchange_name} scraper: {e}")
            continue

async def main():
    # await crawl_announcements()
    save_accoucements_to_csv()

if __name__ == "__main__":
    asyncio.run(main())