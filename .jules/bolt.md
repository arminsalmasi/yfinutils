## 2025-02-19 - Index List Memoization
**Learning:** `get_tickers` reads from the offline DB correctly, but without caching the parsed lists, we re-parse `.get("companies")`, iterate to extract tickers, `.extend()` them, and call `sorted(list(set(tickers)))` every single time it's called. When used repeatedly (e.g. for batch processing across the index), this turns a fast cache lookup into a CPU bottleneck taking over 5.5s for 5000 iterations.
**Action:** Memoize standard parsed lists inside the class instance. This bypasses redundant list processing reducing time to 0.01s. Remember to return a copy or new list to avoid accidental side-effect mutations.

## 2025-02-19 - Vectorized Event Mapping for Pandas DataFrames
**Learning:** When mapping time-series events (like corporate actions, dividends, and stock splits) to a Pandas DataFrame, iterating through events in a Python loop and using `.get_indexer` for each element is extremely slow. This was observed when merging dividend data; the repeated timezone conversions and index lookups create significant overhead.
**Action:** Use vectorized operations. Pass a list of dates to `pd.to_datetime`, localize and convert timezones once, and then call `get_indexer` on the entire array. This approach is multiple orders of magnitude faster (e.g., from 0.1607s to 0.0018s in testing).
