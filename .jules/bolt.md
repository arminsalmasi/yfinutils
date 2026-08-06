## 2025-02-19 - Index List Memoization
**Learning:** `get_tickers` reads from the offline DB correctly, but without caching the parsed lists, we re-parse `.get("companies")`, iterate to extract tickers, `.extend()` them, and call `sorted(list(set(tickers)))` every single time it's called. When used repeatedly (e.g. for batch processing across the index), this turns a fast cache lookup into a CPU bottleneck taking over 5.5s for 5000 iterations.
**Action:** Memoize standard parsed lists inside the class instance. This bypasses redundant list processing reducing time to 0.01s. Remember to return a copy or new list to avoid accidental side-effect mutations.

## 2025-02-19 - Vectorized Corporate Actions
**Learning:** When mapping time-series events (like corporate actions) to a Pandas DataFrame, iterating through events in a Python loop and using `pd.to_datetime` followed by `df.index.get_indexer` for each item causes significant performance overhead (tested at ~2.1s for 1780 actions).
**Action:** Use vectorized operations by extracting all dates into a list, passing them to `pd.to_datetime` at once, and calling `get_indexer` with the vectorized DatetimeIndex. Apply values to the DataFrame using boolean masking. This provides a ~575x speedup (~0.003s).
