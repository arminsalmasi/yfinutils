import re
import requests
import pandas as pd
from io import StringIO
from typing import Dict, List, Optional, Any

# Standard headers to avoid blocking
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# Standard Yahoo Finance Suffixes for Index Components
INDEX_SUFFIX_MAP = {
    "SP500": "",
    "SP100": "",
    "SP600": "",
    "DOW": "",
    "NASDAQ100": "",
    "FTSE100": ".L",
    "FTSE250": ".L",
    "DAX": ".DE",
    "MDAX": ".DE",
    "SDAX": ".DE",
    "TECDAX": ".DE",
    "CAC40": ".PA",
    "CACMID60": ".PA",
    "AEX": ".AS",
    "BEL20": ".BR",
    "SMI20": ".SW",
    "OMX_STOCKHOLM": ".ST",
    "OMX_HELSINKI": ".HE",
    "NIKKEI225": ".T",
    "IBOVESPA": ".SA",
    "NIFTY50": ".NS",
    "NIFTYBANK": ".NS",
    "EUROSTOXX50": "" # Stoxx components vary (e.g. .DE, .PA, .AS depending on origin)
}

def fetch_html(url: str, headers: Optional[Dict[str, str]] = None) -> str:
    """
    Fetch HTML content from a URL with robust error handling and browser headers.
    """
    req_headers = headers or DEFAULT_HEADERS
    response = requests.get(url, headers=req_headers, timeout=15)
    response.raise_for_status()
    return response.text

def normalize_ticker(ticker: str, index_code: Optional[str] = None) -> str:
    """
    Normalize ticker symbols to standard Yahoo Finance format.
    - Replaces '.' or '/' with '-' for US equity classes (e.g., BRK.B -> BRK-B, BF/B -> BF-B).
    - Appends international suffixes based on index if missing (e.g., SHEL -> SHEL.L).
    """
    if not ticker:
        return ""
    
    ticker = str(ticker).strip().upper()
    
    # Check if there is already a suffix (e.g. .L, .DE, .AS)
    has_international_suffix = False
    parts = ticker.split('.')
    if len(parts) == 2:
        suffix = parts[1]
        # Common exchange suffixes are usually upper letters and 1-3 chars (e.g., L, DE, AS, BR, PA, ST, HE, SA, NS, T)
        if len(suffix) >= 1 and suffix.isalpha() and suffix.isupper():
            has_international_suffix = True
            
    # Apply normalization rules
    if index_code in ["SP500", "SP100", "SP600", "DOW", "NASDAQ100"] or not index_code:
        # For US indices, dots or slashes indicate class structure. Replace with '-'
        ticker = ticker.replace('.', '-').replace('/', '-')
    else:
        # For international indices, if it doesn't already have an exchange suffix, append it
        suffix = INDEX_SUFFIX_MAP.get(index_code, "")
        if suffix and not has_international_suffix:
            # First clean any dots
            ticker = ticker.replace('.', '-').replace('/', '-')
            ticker = f"{ticker}{suffix}"
            
    return ticker

def parse_wikipedia_table(url: str, column_mapping: Dict[str, List[str]], table_id_attr: Optional[Dict[str, str]] = None, table_index: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Parse a table from a Wikipedia page using Pandas read_html.
    Returns a list of dictionaries containing the mapped columns.
    """
    html_content = fetch_html(url)
    
    # Read tables
    tables = pd.read_html(StringIO(html_content))
    
    target_table = None
    
    # If a specific table_id_attr (like {"id": "constituents"}) is provided, look for it in HTML
    if table_id_attr:
        # Find which table matches by column headers or try to locate the table index
        # We can scan tables and find the one that contains our required headers
        pass
        
    if table_index is not None and table_index < len(tables):
        target_table = tables[table_index]
    else:
        # Scan tables to find the first table containing at least one matching symbol column
        symbol_candidates = column_mapping.get("symbol", [])
        for df in tables:
            # Check if any symbol column candidate matches a column in df
            if any(col in df.columns for col in symbol_candidates):
                target_table = df
                break
                
    if target_table is None:
        # Fallback to the first table if no clear match
        if tables:
            target_table = tables[0]
        else:
            raise ValueError(f"No tables found on page: {url}")
            
    # Map columns to output structure
    results = []
    
    # Detect the actual columns in target_table that match our mapping
    actual_columns = {}
    for standard_col, candidates in column_mapping.items():
        for candidate in candidates:
            if candidate in target_table.columns:
                actual_columns[standard_col] = candidate
                break
                
    if "symbol" not in actual_columns:
        # If symbol column was not found, check if we can guess it (e.g. first column with strings)
        raise ValueError(f"Could not find symbol column in table. Mappings tried: {column_mapping.get('symbol')}")
        
    for _, row in target_table.iterrows():
        symbol_val = row[actual_columns["symbol"]]
        if pd.isna(symbol_val):
            continue
            
        symbol = str(symbol_val).strip()
        name = str(row[actual_columns["name"]]).strip() if "name" in actual_columns else ""
        country = str(row[actual_columns["country"]]).strip() if "country" in actual_columns else None
        sector = str(row[actual_columns["sector"]]).strip() if "sector" in actual_columns else None
        isin = str(row[actual_columns["isin"]]).strip() if "isin" in actual_columns else None
        
        # Clean clean tags, disambiguations
        if name:
            name = re.sub(r"\s*\[\d+\]\s*$", "", name) # Remove wiki references like [1]
            
        results.append({
            "name": name,
            "raw_symbol": symbol,
            "country": country,
            "sector": sector,
            "isin": isin
        })
        
    return results
