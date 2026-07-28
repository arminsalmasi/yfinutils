## 2025-02-19 - Index List Memoization
**Learning:** `get_tickers` reads from the offline DB correctly, but without caching the parsed lists, we re-parse `.get("companies")`, iterate to extract tickers, `.extend()` them, and call `sorted(list(set(tickers)))` every single time it's called. When used repeatedly (e.g. for batch processing across the index), this turns a fast cache lookup into a CPU bottleneck taking over 5.5s for 5000 iterations.
**Action:** Memoize standard parsed lists inside the class instance. This bypasses redundant list processing reducing time to 0.01s. Remember to return a copy or new list to avoid accidental side-effect mutations.

## 2023-10-27 - Vectorized DataFrame Indexing
**Learning:** In pandas, iterating through time-series events (like dividends/splits) and calling `df.index.get_indexer()` in a loop is extremely slow. A test simulation with 1000 events took ~4.6 seconds.
**Action:** Always extract values into lists, pass them collectively to `pd.to_datetime()`, and call `df.index.get_indexer()` once on the entire array to map events in bulk. This reduced the time from 4.6s to 0.05s.
