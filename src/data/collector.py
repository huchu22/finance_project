"""
Data Collector Module
Fetches price, dividend, and FX data for Korean ETFs, US benchmark ETFs, and USD/KRW.
Aligns trading calendars and provides cached datasets.
"""

from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional
import FinanceDataReader as fdr
import pandas as pd
import yfinance as yf


class MarketDataCollector:
    """Market data collector supporting both Korean market (KRX) and US market."""

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_korean_etf(self, symbol: str, start: str = "2020-01-01", end: Optional[str] = None) -> pd.DataFrame:
        """Fetch Korean ETF daily prices via FinanceDataReader.
        Symbol example: '448330' (TIGER 미국배당다우존스), '379800' (KODEX 미국S&P500TR)
        """
        try:
            df = fdr.DataReader(symbol, start=start, end=end)
            if df.empty:
                # Fallback to yfinance with .KS suffix
                yf_symbol = f"{symbol}.KS"
                ticker = yf.Ticker(yf_symbol)
                df = ticker.history(start=start, end=end)
            df.index = pd.to_datetime(df.index)
            return df
        except Exception as e:
            print(f"[Error] Failed to fetch Korean ETF {symbol}: {e}")
            return pd.DataFrame()

    def get_us_etf(self, ticker_symbol: str, start: str = "2020-01-01", end: Optional[str] = None) -> pd.DataFrame:
        """Fetch US ETF daily prices and dividends via yfinance.
        Ticker example: 'SCHD', 'SPY', 'TLT'
        """
        try:
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(start=start, end=end)
            df.index = pd.to_datetime(df.index).tz_localize(None)
            return df
        except Exception as e:
            print(f"[Error] Failed to fetch US ETF {ticker_symbol}: {e}")
            return pd.DataFrame()

    def get_usdkrw_fx(self, start: str = "2020-01-01", end: Optional[str] = None) -> pd.DataFrame:
        """Fetch USD/KRW exchange rate."""
        try:
            df = fdr.DataReader("USD/KRW", start=start, end=end)
            if df.empty:
                ticker = yf.Ticker("USDKRW=X")
                df = ticker.history(start=start, end=end)
            df.index = pd.to_datetime(df.index).tz_localize(None)
            return df
        except Exception as e:
            print(f"[Error] Failed to fetch USD/KRW: {e}")
            return pd.DataFrame()

    def get_aligned_asset_fx_data(
        self,
        kr_symbol: str,
        us_ticker: str,
        start: str = "2022-01-01",
        end: Optional[str] = None
    ) -> pd.DataFrame:
        """Align Korean ETF, US Benchmark ETF, and USD/KRW on matching business days.
        Applies forward fill to handle differing market holidays between KR and US.
        """
        kr_df = self.get_korean_etf(kr_symbol, start=start, end=end)
        us_df = self.get_us_etf(us_ticker, start=start, end=end)
        fx_df = self.get_usdkrw_fx(start=start, end=end)

        merged = pd.DataFrame(index=pd.date_range(start=start, end=end or datetime.now().strftime("%Y-%m-%d")))
        merged.index.name = "Date"

        if not kr_df.empty:
            merged[f"KR_{kr_symbol}"] = kr_df["Close"]
        if not us_df.empty:
            merged[f"US_{us_ticker}"] = us_df["Close"]
        if not fx_df.empty:
            merged["USDKRW"] = fx_df["Close"]

        # Forward fill missing weekend/holiday data
        merged = merged.ffill().dropna()

        # Synthetic Theoretical Price (US ETF price in KRW converted by FX)
        if f"US_{us_ticker}" in merged.columns and "USDKRW" in merged.columns:
            merged[f"THEORETICAL_{us_ticker}_KRW"] = merged[f"US_{us_ticker}"] * merged["USDKRW"]

        return merged

    def get_user_portfolio_data(
        self,
        symbols: Optional[List[str]] = None,
        start: str = "2023-10-15",
        include_fx: bool = True
    ) -> pd.DataFrame:
        """Fetch daily closing prices for user's 5 exact ETF holdings and FX rate.
        - 360750: TIGER 미국S&P500
        - 379800: KODEX 미국S&P500TR
        - 458730: TIGER 미국배당다우존스
        - 465580: ACE 미국빅테크TOP7 Plus
        - 284430: KODEX 200미국채혼합50
        """
        if symbols is None:
            symbols = ["360750", "379800", "458730", "465580", "284430"]

        series_dict = {}
        for s in symbols:
            df = self.get_korean_etf(s, start=start)
            if not df.empty and "Close" in df.columns:
                series_dict[s] = df["Close"]

        if include_fx:
            fx_df = self.get_usdkrw_fx(start=start)
            if not fx_df.empty and "Close" in fx_df.columns:
                series_dict["USDKRW"] = fx_df["Close"]

        combined = pd.DataFrame(series_dict)
        return combined.ffill().dropna()



if __name__ == "__main__":
    collector = MarketDataCollector()
    print("Testing data collection...")
    fx = collector.get_usdkrw_fx(start="2024-01-01")
    print(f"FX latest ({fx.index[-1].strftime('%Y-%m-%d')}): {fx['Close'].iloc[-1]:.2f} KRW")
    schd = collector.get_us_etf("SCHD", start="2024-01-01")
    print(f"SCHD latest ({schd.index[-1].strftime('%Y-%m-%d')}): ${schd['Close'].iloc[-1]:.2f}")
    tiger = collector.get_korean_etf("448330", start="2024-01-01")
    print(f"TIGER 미국배당다우존스 latest ({tiger.index[-1].strftime('%Y-%m-%d')}): {tiger['Close'].iloc[-1]:,.0f} KRW")
