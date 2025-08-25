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
MAX_DEBUG_SIZE = 5  # Maximum announcements per exchange in debug mode
OFFSET_DAYS = 14
ANALYZER_API_KEY = "sk-790c031d07224ee9a905c970cefffcba"


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

    print(f"Debug mode: {DEBUG_MODE}")
    if DEBUG_MODE:
        print(f"Maximum announcements per exchange: {MAX_DEBUG_SIZE}")

    # Initialize scrapers with debug configuration
    # Instantiate scrapers without sharing a single analyzer; each will create its own
    scrapers = [
        BinanceScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        BingxScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        BitunixScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        BlofinScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        BitgetScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        BtccScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        BybitScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        GateScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        MexcScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        LbankScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        WeexScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        CoinexScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        UpbitScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY),
        OkxScraper(None, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY)
    ]

    # Run scrapers concurrently
    tasks = []
    started_scrapers = []
    for scraper in scrapers:
        run_method = getattr(scraper, "run_scraping", None)
        if run_method is None:
            continue
        print(f"\n=== Starting {scraper.exchange_name} scraper ===")
        if asyncio.iscoroutinefunction(run_method):
            tasks.append(asyncio.create_task(run_method()))
        else:
            tasks.append(asyncio.to_thread(run_method))
        started_scrapers.append(scraper)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for scraper, result in zip(started_scrapers, results):
        if isinstance(result, Exception):
            print(f"Error running {scraper.exchange_name} scraper: {result}")

async def main():
    await crawl_announcements()
    save_accoucements_to_csv()

if __name__ == "__main__":
    asyncio.run(main())