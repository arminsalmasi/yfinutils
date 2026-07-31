## 2025-02-19 - Index List Memoization
**Learning:** `get_tickers` reads from the offline DB correctly, but without caching the parsed lists, we re-parse `.get("companies")`, iterate to extract tickers, `.extend()` them, and call `sorted(list(set(tickers)))` every single time it's called. When used repeatedly (e.g. for batch processing across the index), this turns a fast cache lookup into a CPU bottleneck taking over 5.5s for 5000 iterations.
**Action:** Memoize standard parsed lists inside the class instance. This bypasses redundant list processing reducing time to 0.01s. Remember to return a copy or new list to avoid accidental side-effect mutations.

## 2025-02-19 - Vectorizing Pandas Indexer
**Learning:** Iterating through corporate actions (dividends, stock splits) and individually calling `pd.to_datetime` and `get_indexer()` in Python loops leads to severe performance degradation when processing historical event series against a DataFrame index.
**Action:** Always map time-series events to a Pandas DataFrame using vectorized operations—pass lists of dates to `pd.to_datetime` followed by `get_indexer` to batch-process index alignments.
