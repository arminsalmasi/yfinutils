## 2025-02-19 - Index List Memoization
**Learning:** `get_tickers` reads from the offline DB correctly, but without caching the parsed lists, we re-parse `.get("companies")`, iterate to extract tickers, `.extend()` them, and call `sorted(list(set(tickers)))` every single time it's called. When used repeatedly (e.g. for batch processing across the index), this turns a fast cache lookup into a CPU bottleneck taking over 5.5s for 5000 iterations.
**Action:** Memoize standard parsed lists inside the class instance. This bypasses redundant list processing reducing time to 0.01s. Remember to return a copy or new list to avoid accidental side-effect mutations.

## 2025-02-19 - Vectorizing Pandas Datetime Iteration
**Learning:** In the `ticker.py` script, iterating through time-series events using a Python `for` loop to apply `pd.to_datetime` and `get_indexer` sequentially creates a severe performance bottleneck. Processing them iteratively took ~6.0s for 5000 records, whereas vectorizing operations reduced it to ~0.03s.
**Action:** Whenever mapping independent events onto a Pandas DataFrame's time index, always aggregate values and dates into arrays/lists, parse with `pd.to_datetime` in a single pass, and apply indices using a single vectorized `.get_indexer()` call.
