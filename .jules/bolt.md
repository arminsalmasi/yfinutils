## 2025-02-19 - Index List Memoization
**Learning:** `get_tickers` reads from the offline DB correctly, but without caching the parsed lists, we re-parse `.get("companies")`, iterate to extract tickers, `.extend()` them, and call `sorted(list(set(tickers)))` every single time it's called. When used repeatedly (e.g. for batch processing across the index), this turns a fast cache lookup into a CPU bottleneck taking over 5.5s for 5000 iterations.
**Action:** Memoize standard parsed lists inside the class instance. This bypasses redundant list processing reducing time to 0.01s. Remember to return a copy or new list to avoid accidental side-effect mutations.

## 2025-02-19 - Vectorize Pandas Time-Series Mapping
**Learning:** Iterating through corporate events (dividends/splits) in a Python loop to run `pd.to_datetime` and `get_indexer` for timezone conversions and mapping was a major bottleneck in `yftickers/ticker.py`. It took ~1.14s for 500 events on 10k dates.
**Action:** Use vectorized operations by feeding lists of dates and values to Pandas directly. This dropped execution time to ~0.026s, a massive ~43x speedup. Always vectorize time-series assignments in Pandas.
