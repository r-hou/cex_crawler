import os
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
import asyncio
import glob
import json
import pandas as pd


SPOT_CEX = ["binance", "bingx", "bitget", "bybit", "gate", "mexc", "lbank", 'upbit', 'bithumb', 'coinex']
FUTURES_CEX = ["binance", "bingx", "bitunix", "blofin", "bitget", "btcc", "bybit", "gate", "mexc", "okx", "lbank", "weex"]

def save_accoucements_to_csv():
    files = glob.glob("announcements_json/*.json")
    announcements = []
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)
            data = [{**{"file": file.replace("json", "text")}, **i} for i in data]
            announcements += data
    df = pd.DataFrame(announcements)
    today = pd.to_datetime(pd.Timestamp.now(tz='Asia/Shanghai').strftime("%Y-%m-%d"))
    start_date = today - pd.Timedelta(days=7)
    df["comments"] = ""
    df.loc[(df["time"].isna()) | (df["time"].str.len()<10), "comments"] = "待确定"
    df["time"] = df["time"].fillna(today.strftime("%Y-%m-%d"))
    df["time"] = df["time"].apply(lambda x: today.strftime("%Y-%m-%d") if (pd.isna(x) or x == "" or len(x) < 10) else x)
    df.to_csv("announcements.csv", index=False)
    df = df.drop(columns=["file"])
    # 转换时间列，确保没有时区信息
    df['time'] = pd.to_datetime(df['time'])
    # 过滤最近7天的数据
    df = df[df['time'] >= start_date]
    df["description"] = df.apply(lambda x: x["comments"] + x["action"] + " " + x["symbol"]+"\n", axis=1)
    spot_df = df[(df["type"] == "现货") & df["exchange"].isin(SPOT_CEX)]
    spot_df = spot_df.groupby(["time", "exchange"]).agg({"description": " ".join})
    spot_df = spot_df.reset_index()
    spot_df = spot_df.pivot(index="time", columns="exchange", values="description")
    spot_df.to_csv("announcements_spot.csv", index=True)
    futures_df = df[(df["type"] == "合约") & df["exchange"].isin(FUTURES_CEX)]
    futures_df = futures_df.groupby(["time", "exchange"]).agg({"description": " ".join})
    futures_df = futures_df.reset_index()
    futures_df = futures_df.pivot(index="time", columns="exchange", values="description")
    futures_df.to_csv("announcements_futures.csv", index=True)

async def crawl_announcements():
    if not os.path.exists("announcements_text"):
        os.makedirs("announcements_text", exist_ok=True)

    if not os.path.exists("announcements_json"):
        os.makedirs("announcements_json", exist_ok=True)


    # create analyzer
    analyzer = DeepSeekAnalyzer(api_key="sk-790c031d07224ee9a905c970cefffcba")

    # start binance scraper
    binance_scraper = BinanceScraper(analyzer)
    await binance_scraper.run_scraping()

    # start bingx scraper
    bingx_scraper = BingxScraper(analyzer)
    await bingx_scraper.run_scraping()

    # start bitunix scraper
    bitunix_scraper = BitunixScraper(analyzer)
    await bitunix_scraper.run_scraping()

    # start blofin scraper
    blofin_scraper = BlofinScraper(analyzer)
    await blofin_scraper.run_scraping()

    # start bitget scraper
    bitget_scraper = BitgetScraper(analyzer)
    await bitget_scraper.run_scraping()

    # start btcc scraper
    btcc_scraper = BtccScraper(analyzer)
    btcc_scraper.run_scraping()

    # start bybit scraper
    bybit_scraper = BybitScraper(analyzer)
    bybit_scraper.run_scraping()

    # start gate scraper
    gate_scraper = GateScraper(analyzer)
    gate_scraper.run_scraping()

    # start mexc scraper
    mexc_scraper = MexcScraper(analyzer)
    await mexc_scraper.run_scraping()

    # start okx scraper
    okx_scraper = OkxScraper()
    okx_scraper.run_scraping()

    # start lbank scraper
    lbank_scraper = LbankScraper(analyzer)
    lbank_scraper.run_scraping()

    # start weex scraper
    weex_scraper = WeexScraper(analyzer)
    await weex_scraper.run_scraping()

    # # start bithumb scraper
    # bithumb_scraper = BithumbScraper(analyzer)
    # await bithumb_scraper.run_scraping()

    # start coinex scraper
    coinex_scraper = CoinexScraper(analyzer)
    coinex_scraper.run_scraping()

    # start upbit scraper
    upbit_scraper = UpbitScraper(analyzer)
    upbit_scraper.run_scraping()

async def main():
    # await crawl_announcements()
    save_accoucements_to_csv()

if __name__ == "__main__":
    asyncio.run(main())