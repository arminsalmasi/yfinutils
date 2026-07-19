## 2024-07-19 - Pandas Iterrows Performance
**Learning:** In the `yftickers` codebase, parsing index data from Wikipedia uses Pandas DataFrames. Using `iterrows()` to iterate over DataFrame rows creates a heavy Pandas Series object for each row, resulting in very slow iteration.
**Action:** Always replace `iterrows()` with `to_dict("records")` when row iteration is necessary in pandas. It provides a ~10x speedup with native python dictionary iteration without changing the bracket-notation access syntax.
