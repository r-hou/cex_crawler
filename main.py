import os
import asyncio
import glob
import json
import pandas as pd
import multiprocessing as mp
import concurrent.futures as cf
import traceback
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
from generate_html import generate_static_html

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

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
            if isinstance(data, dict):
                data = [data]
            data = [{**{"file": file}, **i} for i in data]
            announcements += data
    df = pd.DataFrame(announcements)
    today = pd.to_datetime(pd.Timestamp.now(tz='Asia/Shanghai').strftime("%Y-%m-%d"))
    start_date = today - pd.Timedelta(days=7)
    df["comments"] = ""
    df = df[df["time"]!="待定"]
    df.loc[(df["time"].isna()) | (df["time"].str.len()<10), "comments"] = "待确定"
    df["time"] = df["time"].fillna(today.strftime("%Y-%m-%d"))
    df["time"] = df["time"].apply(lambda x: today.strftime("%Y-%m-%d") if (pd.isna(x) or x == "" or len(x) < 10) else x)
    df["release_time"] = pd.to_datetime(df["release_time"])
    df["release_date"] = df["release_time"].dt.date
    df = df.sort_values(by=["release_date", "exchange"], ascending=False)
    df = df.drop(columns=["release_date"])
    df = df[["release_time","time", "exchange", "symbol", "type", "action", "title", "url", "content", "content", "file", "comments"]]
    df = df[df["symbol"].notna() & (df["action"]!="") & df["action"].notna()]
    df.to_csv("announcements.csv", index=False)
    df = df.drop(columns=["file"])
    # 转换时间列，确保没有时区信息
    df['time'] = pd.to_datetime(df['time'])
    # 过滤最近7天的数据
    df = df[df['time'] >= start_date]
    df = df[df["release_time"] >= today-pd.Timedelta(days=OFFSET_DAYS)]
    # df = df[df["content"].isna()]
    # print(df[df["symbol"].isna()])
    print(df[df["symbol"].isna()])
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

def run_scraper_entry(scraper_name: str, debug: bool, max_size: int, offset_days: int, analyzer_api_key: str):
    """Child process entry to run a single scraper in isolation."""
    try:
        # Local import map
        name_to_class = {
            "binance": BinanceScraper,
            "bingx": BingxScraper,
            "bitunix": BitunixScraper,
            "blofin": BlofinScraper,
            "bitget": BitgetScraper,
            "btcc": BtccScraper,
            "bybit": BybitScraper,
            "gate": GateScraper,
            "mexc": MexcScraper,
            "lbank": LbankScraper,
            "weex": WeexScraper,
            "coinex": CoinexScraper,
            "upbit": UpbitScraper,
            "okx": OkxScraper,
        }
        cls = name_to_class.get(scraper_name)
        if cls is None:
            print(f"Unknown scraper: {scraper_name}")
            return
        print(f"\n=== [Process] Starting {scraper_name} scraper ===")
        # Instantiate with best-effort constructor compatibility
        try:
            scraper = cls(None, debug, max_size, offset_days, ANALYZER_API_KEY)
        except TypeError:
            try:
                scraper = cls(None, debug, max_size, offset_days)
            except TypeError:
                try:
                    scraper = cls()
                except Exception as e:
                    print(f"Failed to construct {scraper_name}: {e}")
                    return

        run_method = getattr(scraper, "run_scraping", None)
        if run_method is None:
            print(f"{scraper_name} has no run_scraping method")
            return
        import asyncio as _asyncio
        if _asyncio.iscoroutinefunction(run_method):
            _asyncio.run(run_method())
        else:
            run_method()
    except Exception as e:
        print(f"[Process] Error in {scraper_name}: {traceback.format_exc()}")


async def crawl_announcements():
    # Ensure output directory exists
    if not os.path.exists("output"):
        os.makedirs("output", exist_ok=True)

    print(f"Debug mode: {DEBUG_MODE}")
    if DEBUG_MODE:
        print(f"Maximum announcements per exchange: {MAX_DEBUG_SIZE}")

    # Initialize scrapers with debug configuration
    # Run each scraper in its own process via ProcessPoolExecutor
    scraper_names = [
        # "binance", 
        # "bingx", 
        # "bitunix", 
        # "blofin", 
        # "bitget", 
        "btcc", 
        # "bybit",
        # "gate",
        # "mexc",
        # "lbank", 
        # "weex", 
        # "coinex", 
        # "upbit", 
        # "okx"
    ]

    max_workers = min(len(scraper_names), (os.cpu_count() or 4))
    with cf.ProcessPoolExecutor(max_workers=max_workers, mp_context=mp.get_context("spawn")) as executor:
        futures = [
            executor.submit(run_scraper_entry, name, DEBUG_MODE, MAX_DEBUG_SIZE, OFFSET_DAYS, ANALYZER_API_KEY)
            for name in scraper_names
        ]
        for fut, name in zip(futures, scraper_names):
            try:
                fut.result()
            except Exception as e:
                print(f"[ProcessPool] Error in {name}: {traceback.format_exc()}")

async def main():
    await crawl_announcements()
    save_accoucements_to_csv()
    generate_static_html()

if __name__ == "__main__":
    asyncio.run(main())