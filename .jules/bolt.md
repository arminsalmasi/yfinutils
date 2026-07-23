## 2024-05-18 - Vectorize Pandas Timezone Operations
**Learning:** Calling `pd.to_datetime(...).tz_localize(...).tz_convert(...)` inside a python loop for every single event (e.g. corporate actions) is extremely slow due to the overhead of instantiating DatetimeIndex and converting timezones repeatedly.
**Action:** Always construct lists of dates first, pass them all to `pd.to_datetime(..., utc=True)`, and perform timezone conversion/localization on the entire series at once using vectorization. This yields a massive (~100x+) speedup when dealing with arrays of events mapped to a DataFrame.
