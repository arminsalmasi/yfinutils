## 2025-02-19 - Index List Memoization
**Learning:** `get_tickers` reads from the offline DB correctly, but without caching the parsed lists, we re-parse `.get("companies")`, iterate to extract tickers, `.extend()` them, and call `sorted(list(set(tickers)))` every single time it's called. When used repeatedly (e.g. for batch processing across the index), this turns a fast cache lookup into a CPU bottleneck taking over 5.5s for 5000 iterations.
**Action:** Memoize standard parsed lists inside the class instance. This bypasses redundant list processing reducing time to 0.01s. Remember to return a copy or new list to avoid accidental side-effect mutations.

## 2025-02-19 - Vectorize Timeseries Event Mapping
**Learning:** When mapping time-series events (like dividends or stock splits) to a Pandas DataFrame, iterating through events in a Python loop and calling `pd.to_datetime` and `get_indexer` sequentially causes significant performance overhead (~0.12s per 100 events).
**Action:** Always use vectorized operations for event mapping by aggregating dates and values into lists, processing them with a single `pd.to_datetime` call, and applying updates via bulk boolean masks (reduces time to ~0.0015s).
