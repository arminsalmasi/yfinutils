# yftickers 🚀

[![PyPI version](https://img.shields.io/pypi/v/yftickers.svg)](https://pypi.org/project/yftickers/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()

A unified, highly optimized, and robust Python library designed to retrieve, scrape, and format stock tickers in **Yahoo Finance format** across global indices and US markets.

It unifies the exhaustive index mapping of `pytickersymbols` with the simple dynamic scraping interfaces of `yahoo-fin`, and scales symbol discovery to the entire US market utilizing direct FTP integration with NASDAQ Trader. It includes **concurrent parallel scraping** (via a ThreadPool) and a **rich offline cache fallback** ensuring lightning-fast performance under any network condition.

---

## Key Features 🌟

*   **⚡ Lightning-Fast Performance:** Integrated with an offline cache (`cached_indices.json`) loaded in microseconds, allowing instant lookup with **zero network requests**.
*   **🌐 Broad Global Index Coverage:** Fully supports S&P 500, NASDAQ 100, Dow Jones, FTSE 100, FTSE 250, DAX, MDAX, SDAX, TecDAX, CAC 40, CAC Mid 60, AEX, BEL 20, Swiss Market Index (SMI 20), OMX Stockholm 30, OMX Helsinki 25, NIKKEI 225, Ibovespa, and Nifty 50.
*   **🛠️ Parallel Multi-threaded Scraping:** Live-scrapes multiple indices simultaneously in a thread pool using `ThreadPoolExecutor`—up to **8x faster** than sequential scrapers.
*   **⚙️ Smart Exchange Suffix Normalization:** Automatically handles US ticker class naming (e.g. `BRK.B` -> `BRK-B`) and correctly appends exchange suffixes for international markets (e.g., `.L` for London, `.DE` for Frankfurt, `.SA` for Sao Paulo, `.NS` for India, `.T` for Tokyo).
*   **🔌 Direct NASDAQ FTP Integration:** Download the entire universe of US listed stocks (NASDAQ, NYSE, AMEX, ARCA) directly from NASDAQ's FTP server.
*   **💾 Flexible Export Formats:** Export ticker sets, standard string lists, or complete company metadata structures (name, sector, industry, country, ISIN) to JSON.

---

## Installation 📦

Install `yftickers` from PyPI using pip:

```bash
pip install yftickers
```

---

## Quick Start 🚀

### 1. Instant Lookup (Offline Cache Mode)
Retrieve tickers in microseconds with no network traffic.

```python
from yftickers import YahooFinanceTickers

# Initialize the engine
yft = YahooFinanceTickers()

# Get tickers for S&P 500
sp500 = yft.get_tickers("SP500")
print(f"Loaded {len(sp500)} S&P 500 tickers. Example: {sp500[:3]}")
# Output: Loaded 503 S&P 500 tickers. Example: ['A', 'AAL', 'AAPL']

# Get DAX tickers with Frankfurt suffixes (.DE)
dax = yft.get_tickers("DAX")
print(f"Loaded {len(dax)} DAX tickers. Example: {dax[:3]}")
# Output: Loaded 40 DAX tickers. Example: ['1COV.DE', 'ADS.DE', 'ALV.DE']
```

### 2. Live Scraped Index Lookup (Live Mode)
Scrape Wikipedia live to get real-time constituent lists.

```python
# Force a live scrape to get the most up-to-date constituents
live_sp500 = yft.get_tickers("SP500", force_scrape=True)
print(f"Live-scraped {len(live_sp500)} tickers.")
```

### 3. Fetch Comprehensive Metadata
Retrieve full company details, including names, sectors, industries, ISINs, and countries.

```python
ftse_meta = yft.get_metadata("FTSE100")
for company in ftse_meta[:3]:
    print(f"Company: {company['name']} | Ticker: {company['ticker']} | Sector: {company['sector']}")
# Output:
# Company: AstraZeneca | Ticker: AZN.L | Sector: Healthcare
# Company: BP | Ticker: BP.L | Sector: Energy
```

### 4. Bulk Concurrent Scraping (Server Sync)
Scrape all supported indexes in parallel using Python's ThreadPoolExecutor.

```python
# Live-scrape all global indices concurrently
all_live_data = yft.scrape_all_indices(use_threads=True, max_workers=8)

for index, companies in all_live_data.items():
    print(f"Index {index}: Scraped {len(companies)} companies.")
```

### 5. Download Entire US Stock Market (NASDAQ FTP)
Pull and format lists of all publicly traded stocks from the NASDAQ Trader FTP.

```python
# Download NASDAQ listed stocks
nasdaq_listed = yft.download_nasdaq_tickers()
print(f"Active NASDAQ stocks: {len(nasdaq_listed)}")

# Download other listed stocks (NYSE, AMEX, ARCA)
other_listed = yft.download_other_tickers()
print(f"Other public US stocks: {len(other_listed)}")
```

### 6. Export Ticker Lists to JSON
Easily save your query results to standard files.

```python
# Save SP500 tickers list
yft.save_to_json(sp500, "sp500_tickers.json")

# Save enriched metadata
yft.save_to_json(ftse_meta, "ftse_metadata.json")
```

---

## API Reference 📚

### `YahooFinanceTickers(cache_file_path=None)`
Core engine class. If `cache_file_path` is omitted, uses the rich pre-compiled local database.

*   `get_available_indices() -> List[str]`
    Returns list of index keys supported by the engine.
*   `get_tickers(index_name: str, force_scrape: bool = False) -> List[str]`
    Returns sorted list of Yahoo Finance tickers for the index.
*   `get_metadata(index_name: str, force_scrape: bool = False) -> List[Dict[str, Any]]`
    Returns complete company lists with metadata dicts.
*   `scrape_index(index_name: str) -> List[Dict[str, Any]]`
    Live scrapes Wikipedia for the specified index.
*   `scrape_all_indices(use_threads: bool = True, max_workers: int = 8) -> Dict[str, List[Dict[str, Any]]]`
    Scrapes all global indices concurrently.
*   `download_nasdaq_tickers() -> List[str]`
    Downloads all symbols listed on NASDAQ via FTP.
*   `download_other_tickers() -> List[str]`
    Downloads other exchange-listed symbols (NYSE, AMEX) via FTP.
*   `save_to_json(data: Any, filepath: str) -> None`
    Serializes standard dictionary/list objects into clean JSON files.

---

## Optimized Historical Market Data Client 📊

`yftickers` now supports robust historical stock market data downloading, featuring highly optimized connection pooling, automated rate-limit backing off, cookie/crumb synchronization, and concurrent batch fetching.

### 1. Retrieve Single Ticker Data (Ticker API)
Retrieve historical prices, dividend records, stock splits, and real-time quote metadata with the intuitive `Ticker` class.

```python
from yftickers import Ticker

# Initialize the Ticker
ticker = Ticker("AAPL")

# Fetch 1 month of historical pricing at 1-day interval (OHLCV + Actions)
hist = ticker.history(period="1mo", interval="1d", auto_adjust=True)
print(hist.head())

# Fetch fundamental & quote metadata dynamically
info = ticker.info
print(f"Company Name: {info.get('longName')} | Market Cap: {info.get('marketCap')}")

# Fetch corporate actions (dividends and splits)
print("Dividends history:")
print(ticker.dividends.head())

print("Stock Splits history:")
print(ticker.splits.head())
```

### 2. High-Speed Bulk Concurrent Downloads
Batch-fetch historical data for hundreds of stocks simultaneously using optimized thread pools and connection-pooled HTTP clients.

```python
import yftickers

# Download S&P 500 constituents or a custom ticker set in parallel
tickers = "AAPL MSFT GOOGL TSLA"
data = yftickers.download(tickers, period="3mo", interval="1d", auto_adjust=True, progress=True)

# The result is grouped by Metric with a Pandas MultiIndex (Metric -> Ticker)
print(data["Close"].head())
```

---

## Technical Optimizations ⚡

Unlike standard libraries, `yftickers` is engineered from the ground up for high speed and robust resource utilization:
1. **Persistent Connection Pooling:** Leverages a thread-safe global `requests.Session` mounted with connection-pooled adapters (`pool_connections=100`, `pool_maxsize=100`), reducing latency by reusing active TLS sockets during concurrent requests.
2. **Robust Cookie & Crumb Resolution:** Employs an automated, cached, thread-locked cookie-consent and crumb fetching system mimicking real browser flows, mitigating unauthorized (`401`) and rate-limit (`429`) errors.
3. **Adaptive Back-Off Retries:** Integrates automatic retry adapters that exponentially back off during rate limits or server degradation.

---

## Inspiration & Acknowledgements 💖

This library builds upon, refines, and is inspired by the exceptional work of the following open-source financial packages:
- **[yfinance](https://github.com/ranaroussi/yfinance)**: The standard-bearer Python library for Yahoo Finance. Our `Ticker` pricing, historical parsing, action alignments, and `download` structure are inspired by `yfinance`'s robust design. Developed under the permissive **Apache License 2.0**.
- **[pytickersymbols](https://github.com/0x8b/pytickersymbols)**: An outstanding, exhaustive repository for global index components. The constituent index structures and maps are directly inspired by `pytickersymbols`' excellent layout. Licensed under the **MIT License**.
- **[yahoo-fin](https://github.com/israel-dryer/yahoo-fin)**: A simple, user-friendly package for Yahoo Finance scraping. The core FTP direct integration concept and modular scraping flows draw inspiration from `yahoo-fin`. Licensed under the **MIT License**.

We are deeply grateful to the authors and contributors of these libraries for their contributions to the Python financial ecosystem.

---

## Developer Guide & Releasing 🛠️

### Running Tests
To run unit tests:
```bash
python3 -m unittest discover -s tests
```

### Releasing to PyPI
To bundle and upload the package to PyPI:
1.  **Build distributions:**
    ```bash
    python3 -m pip install --upgrade build twine
    python3 -m build
    ```
2.  **Upload using Twine:**
    ```bash
    python3 -m twine upload dist/*
    ```

---

## License 📄
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
