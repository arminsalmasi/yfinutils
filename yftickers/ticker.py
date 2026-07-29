import datetime
import logging
import pandas as pd
import numpy as np
from typing import Optional, Union, Dict, Any

from yftickers.session import yahoo_session
from yftickers.utils import normalize_ticker

logger = logging.getLogger(__name__)

class Ticker:
    """
    Highly optimized and reliable Yahoo Finance Ticker data extraction client.
    Reuses connection pools, caches cookies/crumbs, handles rate limits,
    and supports precise Pandas DataFrame formatting with timezone support.
    """
    def __init__(self, symbol: str):
        # Normalize symbol automatically to Yahoo Finance standard format
        self.ticker = normalize_ticker(symbol).strip().upper()
        self._info: Optional[Dict[str, Any]] = None
        self._dividends: Optional[pd.Series] = None
        self._splits: Optional[pd.Series] = None

    def __repr__(self) -> str:
        return f"yftickers.Ticker object <{self.ticker}>"

    def _parse_date(self, val: Any) -> Optional[int]:
        """Convert string, date, datetime or timestamp into an integer epoch (seconds)."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return int(val)
        try:
            dt = pd.to_datetime(val)
            if dt.tzinfo is None:
                # Localize naive datetime to UTC to get a standard timestamp
                dt = dt.tz_localize("UTC")
            return int(dt.timestamp())
        except Exception as e:
            logger.error(f"Error parsing date {val}: {e}")
            return None

    def history(
        self,
        period: str = "1mo",
        interval: str = "1d",
        start: Optional[Union[str, datetime.date, datetime.datetime, int]] = None,
        end: Optional[Union[str, datetime.date, datetime.datetime, int]] = None,
        prepost: bool = False,
        actions: bool = True,
        auto_adjust: bool = True,
        proxy: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Download historical market data for the ticker.
        
        Parameters:
        - period: data period to download (e.g., "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
        - interval: data interval (e.g., "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")
        - start: starting date (string "YYYY-MM-DD", date, datetime, or epoch integer)
        - end: ending date (string "YYYY-MM-DD", date, datetime, or epoch integer)
        - prepost: include pre and post market data
        - actions: download dividends and stock splits events
        - auto_adjust: adjust OHLC based on the Adj Close column
        - proxy: HTTP proxy (if any)
        
        Returns:
        - pandas.DataFrame with pricing data and optional actions columns.
        """
        # Resolve target chart URL
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{self.ticker}"
        
        params: Dict[str, Any] = {
            "interval": interval,
            "includeAdjustedClose": "true",
        }
        
        if prepost:
            params["includePrePost"] = "true"
        else:
            params["includePrePost"] = "false"
            
        if actions:
            params["events"] = "div,splits"
        else:
            params["events"] = ""

        # Parse start/end dates if provided
        start_epoch = self._parse_date(start)
        end_epoch = self._parse_date(end)
        
        if start_epoch is not None:
            params["period1"] = start_epoch
            if end_epoch is not None:
                params["period2"] = end_epoch
            else:
                # Default end to current time
                params["period2"] = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        else:
            params["range"] = period

        # Handle custom proxy temporarily if provided
        prev_proxies = None
        if proxy:
            prev_proxies = yahoo_session.session.proxies
            yahoo_session.session.proxies = {"http": proxy, "https": proxy}

        try:
            resp = yahoo_session.execute_request(url, params=params)
        finally:
            if proxy and prev_proxies is not None:
                yahoo_session.session.proxies = prev_proxies

        if resp.status_code != 200:
            logger.warning(f"Failed to retrieve history for {self.ticker} (status: {resp.status_code})")
            return self._empty_dataframe()

        try:
            data = resp.json()
        except Exception as e:
            logger.error(f"Failed to parse history JSON for {self.ticker}: {e}")
            return self._empty_dataframe()

        chart_result = data.get("chart", {}).get("result", [])
        if not chart_result:
            error_msg = data.get("chart", {}).get("error", {}).get("description", "Unknown error")
            logger.warning(f"No chart data returned for {self.ticker}. Error: {error_msg}")
            return self._empty_dataframe()

        result = chart_result[0]
        timestamps = result.get("timestamp", [])
        if not timestamps:
            return self._empty_dataframe()

        meta = result.get("meta", {})
        tz_name = meta.get("exchangeTimezoneName", "UTC")
        
        indicators = result.get("indicators", {})
        quote_list = indicators.get("quote", [])
        if not quote_list:
            return self._empty_dataframe()
            
        quote = quote_list[0]
        adjclose = indicators.get("adjclose", [{}])[0].get("adjclose", [])

        # Build initial pricing DataFrame with length-aligned arrays to handle incomplete API mocks or responses
        n_timestamps = len(timestamps)
        def _get_aligned_list(key):
            lst = quote.get(key)
            if lst is None or len(lst) != n_timestamps:
                return [np.nan] * n_timestamps
            return lst

        df = pd.DataFrame({
            "Open": _get_aligned_list("open"),
            "High": _get_aligned_list("high"),
            "Low": _get_aligned_list("low"),
            "Close": _get_aligned_list("close"),
            "Volume": _get_aligned_list("volume"),
        })
        
        # Ensure all columns are float except Volume (which is integer, keeping float to allow NaNs)
        for col in ["Open", "High", "Low", "Close"]:
            if col in df.columns:
                df[col] = df[col].astype(float)
        if "Volume" in df.columns:
            df["Volume"] = df["Volume"].fillna(0).astype(float)

        if adjclose:
            df["Adj Close"] = [float(x) if x is not None else np.nan for x in adjclose]
        else:
            df["Adj Close"] = df["Close"]

        # Set up datetime index localized to exchange timezone
        try:
            df.index = pd.to_datetime(timestamps, unit="s")
            df.index = df.index.tz_localize("UTC").tz_convert(tz_name)
        except Exception as e:
            logger.warning(f"Timezone conversion failed for {self.ticker}: {e}")
            df.index = pd.to_datetime(timestamps, unit="s")

        # Sort index to ensure chronological order
        df = df.sort_index()

        # Parse actions (Dividends and Stock Splits) if requested
        if actions:
            df["Dividends"] = 0.0
            df["Stock Splits"] = 0.0
            
            events = result.get("events", {})
            dividends = events.get("dividends", {})
            splits = events.get("splits", {})
            
            # Map dividends (Vectorized)
            if dividends:
                div_items = list(dividends.values())
                div_dates = [item["date"] for item in div_items]
                div_amounts = [float(item["amount"]) for item in div_items]

                div_times = pd.to_datetime(div_dates, unit="s").tz_localize("UTC").tz_convert(tz_name)
                pos = df.index.get_indexer(div_times, method="nearest")

                valid_mask = pos != -1
                if valid_mask.any():
                    valid_pos = pos[valid_mask]
                    valid_amounts = np.array(div_amounts)[valid_mask]
                    df.iloc[valid_pos, df.columns.get_loc("Dividends")] = valid_amounts
            
            # Map stock splits (Vectorized)
            if splits:
                split_items = list(splits.values())
                split_dates = [item["date"] for item in split_items]
                split_ratios = [
                    float(item.get("numerator", 1)) / float(item.get("denominator", 1))
                    for item in split_items
                ]

                split_times = pd.to_datetime(split_dates, unit="s").tz_localize("UTC").tz_convert(tz_name)
                pos = df.index.get_indexer(split_times, method="nearest")

                valid_mask = pos != -1
                if valid_mask.any():
                    valid_pos = pos[valid_mask]
                    valid_ratios = np.array(split_ratios)[valid_mask]
                    df.iloc[valid_pos, df.columns.get_loc("Stock Splits")] = valid_ratios

        # Apply auto adjustments if requested
        if auto_adjust and "Adj Close" in df.columns:
            # Avoid division by zero
            close_values = df["Close"].to_numpy()
            close_values_safe = np.where(close_values == 0, np.nan, close_values)
            ratio = df["Adj Close"].to_numpy() / close_values_safe
            ratio = np.nan_to_num(ratio, nan=1.0)
            
            df["Open"] = df["Open"] * ratio
            df["High"] = df["High"] * ratio
            df["Low"] = df["Low"] * ratio
            df["Close"] = df["Adj Close"]
            df = df.drop(columns=["Adj Close"])

        df.index.name = "Date"
        return df

    def _empty_dataframe(self) -> pd.DataFrame:
        """Helper to return an empty DataFrame with standard columns."""
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"])
        df.index.name = "Date"
        return df

    @property
    def info(self) -> Dict[str, Any]:
        """
        Fetch real-time quote metadata & fundamentals from Yahoo Finance.
        Returns a dictionary.
        """
        if self._info is not None:
            return self._info
            
        url = f"https://query2.finance.yahoo.com/v6/finance/quote?symbols={self.ticker}"
        try:
            resp = yahoo_session.execute_request(url)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("quoteResponse", {}).get("result", [])
                if results:
                    self._info = results[0]
                    return self._info
        except Exception as e:
            logger.error(f"Error fetching quote info for {self.ticker}: {e}")
            
        return {}

    @property
    def dividends(self) -> pd.Series:
        """Get dividends history as a Pandas Series."""
        if self._dividends is not None:
            return self._dividends
        df = self.history(period="max", actions=True, auto_adjust=False)
        if "Dividends" in df.columns:
            self._dividends = df[df["Dividends"] > 0]["Dividends"]
        else:
            self._dividends = pd.Series(dtype=float, name="Dividends")
            self._dividends.index.name = "Date"
        return self._dividends

    @property
    def splits(self) -> pd.Series:
        """Get stock splits history as a Pandas Series."""
        if self._splits is not None:
            return self._splits
        df = self.history(period="max", actions=True, auto_adjust=False)
        if "Stock Splits" in df.columns:
            self._splits = df[df["Stock Splits"] > 0]["Stock Splits"]
        else:
            self._splits = pd.Series(dtype=float, name="Stock Splits")
            self._splits.index.name = "Date"
        return self._splits

    @property
    def actions(self) -> pd.DataFrame:
        """Get both dividends and stock splits as a combined DataFrame."""
        df = self.history(period="max", actions=True, auto_adjust=False)
        if "Dividends" in df.columns and "Stock Splits" in df.columns:
            actions_df = df[(df["Dividends"] > 0) | (df["Stock Splits"] > 0)][["Dividends", "Stock Splits"]]
            return actions_df
        
        empty_df = pd.DataFrame(columns=["Dividends", "Stock Splits"])
        empty_df.index.name = "Date"
        return empty_df
