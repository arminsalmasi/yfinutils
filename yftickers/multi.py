import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from typing import Union, List, Optional, Dict

from yftickers.ticker import Ticker

logger = logging.getLogger(__name__)

class SimpleProgressBar:
    """
    Extremely lightweight, thread-safe progress bar to monitor downloads
    without external heavy dependencies like tqdm.
    """
    def __init__(self, total: int, text: str = 'completed'):
        self.total = total
        self.count = 0
        self.text = text

    def update(self, n: int = 1):
        if self.total <= 0:
            return
        self.count += n
        percent = 100.0 * self.count / self.total
        bar_len = int(40 * self.count / self.total)
        bar_len = max(0, min(40, bar_len))
        bar = '#' * bar_len + '-' * (40 - bar_len)
        sys.stdout.write(f"\r[{bar}] {percent:.1f}% {self.text}")
        sys.stdout.flush()

    def done(self):
        sys.stdout.write("\n")
        sys.stdout.flush()

def download(
    tickers: Union[str, List[str]],
    period: str = "1mo",
    interval: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
    group_by: str = "column",
    auto_adjust: bool = True,
    threads: bool = True,
    max_workers: Optional[int] = None,
    proxy: Optional[str] = None,
    progress: bool = True
) -> pd.DataFrame:
    """
    Download historical market data for multiple tickers in parallel.
    Reuses pooled connections for speed and resource efficiency.
    
    Parameters:
    - tickers: Single ticker string, list of ticker strings, or space/comma separated ticker string.
    - period: Period to fetch (e.g., "1mo", "1y", "max")
    - interval: Data interval (e.g., "1d", "1h", "1m")
    - start: Start date (string, date, or datetime)
    - end: End date (string, date, or datetime)
    - group_by: How to group columns ("column" or "ticker"). Default is "column".
    - auto_adjust: Adjust OHLC prices automatically
    - threads: Use multi-threading to speed up downloading
    - max_workers: Maximum number of worker threads
    - proxy: HTTP proxy
    - progress: Display progress bar
    
    Returns:
    - pandas.DataFrame containing pricing columns. If multiple tickers are downloaded,
      returns a MultiIndex columns DataFrame.
    """
    # 1. Parse Tickers
    if isinstance(tickers, str):
        # Support space and comma separated symbols
        ticker_list = [t.strip().upper() for t in tickers.replace(",", " ").split() if t.strip()]
    else:
        ticker_list = [str(t).strip().upper() for t in tickers if str(t).strip()]
        
    # Maintain unique list while preserving order
    unique_tickers = list(dict.fromkeys(ticker_list))
    
    if not unique_tickers:
        logger.warning("No valid tickers provided for download.")
        return pd.DataFrame()

    results: Dict[str, pd.DataFrame] = {}
    total_count = len(unique_tickers)
    
    if progress:
        pbar = SimpleProgressBar(total_count, text=f"Tickers downloaded")
        pbar.update(0)

    # 2. Download helper
    def _fetch_one(sym: str) -> tuple:
        ticker = Ticker(sym)
        try:
            df = ticker.history(
                period=period,
                interval=interval,
                start=start,
                end=end,
                actions=True,
                auto_adjust=auto_adjust,
                proxy=proxy
            )
            return sym, df
        except Exception as e:
            logger.error(f"Failed downloading data for ticker '{sym}': {e}")
            return sym, ticker._empty_dataframe()

    # 3. Handle Parallel or Sequential Execution
    if threads and total_count > 1:
        workers = max_workers if max_workers is not None else min(32, total_count)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_ticker = {executor.submit(_fetch_one, t): t for t in unique_tickers}
            for future in as_completed(future_to_ticker):
                sym, df = future.result()
                results[sym] = df
                if progress:
                    pbar.update(1)
    else:
        for sym in unique_tickers:
            sym, df = _fetch_one(sym)
            results[sym] = df
            if progress:
                pbar.update(1)

    if progress:
        pbar.done()

    # 4. Format Output
    if total_count == 1:
        # Return single DataFrame for single ticker download
        single_ticker = unique_tickers[0]
        return results[single_ticker]

    # Combine into a single MultiIndex DataFrame
    # pd.concat handles alignment across different indices beautifully!
    combined_df = pd.concat(results.values(), axis=1, keys=results.keys())
    
    # Structure of combined_df columns is MultiIndex: (Ticker, Metric)
    if group_by == "column":
        # yfinance default: Metric is top level, Ticker is second level
        combined_df.columns = combined_df.columns.swaplevel(0, 1)
        combined_df = combined_df.sort_index(axis=1)
    elif group_by == "ticker":
        # Keep Ticker as top level
        pass
        
    return combined_df
