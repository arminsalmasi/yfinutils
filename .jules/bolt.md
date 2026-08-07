## 2025-02-19 - Index List Memoization
**Learning:** `get_tickers` reads from the offline DB correctly, but without caching the parsed lists, we re-parse `.get("companies")`, iterate to extract tickers, `.extend()` them, and call `sorted(list(set(tickers)))` every single time it's called. When used repeatedly (e.g. for batch processing across the index), this turns a fast cache lookup into a CPU bottleneck taking over 5.5s for 5000 iterations.
**Action:** Memoize standard parsed lists inside the class instance. This bypasses redundant list processing reducing time to 0.01s. Remember to return a copy or new list to avoid accidental side-effect mutations.

## 2025-02-24 - Vectorized Pandas Event Mapping
**Learning:** Iterating through corporate actions (dividends, splits) in a Python loop and repeatedly using `df.index.get_indexer` for each datetime object introduces substantial overhead. It processes each event sequentially, defeating the purpose of fast dataframe lookups.
**Action:** Use Pandas vectorized operations: extract all dates into a list, convert to datetimes collectively using `pd.to_datetime`, and pass the array of times to `df.index.get_indexer` once. This provides nearly a 100x speedup for mapping many time-series events into an existing dataframe.
