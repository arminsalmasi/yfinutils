## 2025-02-19 - Index List Memoization
**Learning:** `get_tickers` reads from the offline DB correctly, but without caching the parsed lists, we re-parse `.get("companies")`, iterate to extract tickers, `.extend()` them, and call `sorted(list(set(tickers)))` every single time it's called. When used repeatedly (e.g. for batch processing across the index), this turns a fast cache lookup into a CPU bottleneck taking over 5.5s for 5000 iterations.
**Action:** Memoize standard parsed lists inside the class instance. This bypasses redundant list processing reducing time to 0.01s. Remember to return a copy or new list to avoid accidental side-effect mutations.

## 2025-02-19 - Corporate Actions Vectorization
**Learning:** In `yftickers/ticker.py`, mapping corporate actions (Dividends and Stock Splits) to a Pandas DataFrame by iterating over events and using `pd.to_datetime(...)` followed by `df.index.get_indexer(...)` for each single event is extremely slow (O(n) operations).
**Action:** When mapping time-series events to a Pandas DataFrame, use vectorized operations: pass the full list of dates to `pd.to_datetime`, find closest index positions for all times at once using `get_indexer`, use array masking `positions != -1` for valid indices, and use `df.iloc` to bulk assign the mapped amounts or ratios.
