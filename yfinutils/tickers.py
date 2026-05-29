import os
import json
import ftplib
import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set, Union, Optional, Any

from yfinutils.utils import (
    normalize_ticker,
    parse_wikipedia_table,
    DEFAULT_HEADERS,
    INDEX_SUFFIX_MAP
)

logger = logging.getLogger(__name__)

# Wikipedia Scraper Configuration
INDEX_SCRAPE_CONFIG = {
    "SP500": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "columns": {
            "symbol": ["Symbol", "Ticker"],
            "name": ["Security", "Company", "Name"],
            "sector": ["GICS Sector", "Sector"],
            "country": ["Headquarters Location", "Country"]
        }
    },
    "SP100": {
        "url": "https://en.wikipedia.org/wiki/S%26P_100",
        "columns": {
            "symbol": ["Symbol", "Ticker"],
            "name": ["Name", "Company"],
            "sector": ["Sector"]
        }
    },
    "SP600": {
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
        "columns": {
            "symbol": ["Ticker symbol", "Symbol"],
            "name": ["Company", "Security"],
            "sector": ["GICS Sector", "Sector"]
        }
    },
    "DOW": {
        "url": "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
        "columns": {
            "symbol": ["Symbol", "Ticker"],
            "name": ["Company"],
            "sector": ["Industry", "Sector"]
        }
    },
    "NASDAQ100": {
        "url": "https://en.wikipedia.org/wiki/NASDAQ-100",
        "columns": {
            "symbol": ["Ticker", "Symbol"],
            "name": ["Company"],
            "sector": ["GICS Sector", "Industry", "Subsector"]
        }
    },
    "FTSE100": {
        "url": "https://en.wikipedia.org/wiki/FTSE_100_Index",
        "columns": {
            "symbol": ["EPIC", "Ticker", "Symbol"],
            "name": ["Company"],
            "sector": ["FTSE Industry Classification Benchmark sector", "Sector"]
        }
    },
    "FTSE250": {
        "url": "https://en.wikipedia.org/wiki/FTSE_250_Index",
        "columns": {
            "symbol": ["Ticker"],
            "name": ["Company"]
        }
    },
    "DAX": {
        "url": "https://en.wikipedia.org/wiki/DAX",
        "columns": {
            "symbol": ["Ticker symbol", "Symbol"],
            "name": ["Company", "Name"],
            "sector": ["Prime Standard Sector", "Sector", "Industry"]
        }
    },
    "MDAX": {
        "url": "https://en.wikipedia.org/wiki/MDAX",
        "columns": {
            "symbol": ["Ticker symbol", "Symbol"],
            "name": ["Company", "Name"],
            "sector": ["Sector"]
        }
    },
    "SDAX": {
        "url": "https://en.wikipedia.org/wiki/SDAX",
        "columns": {
            "symbol": ["Ticker symbol", "Symbol"],
            "name": ["Company", "Name"],
            "sector": ["Sector"]
        }
    },
    "TECDAX": {
        "url": "https://de.wikipedia.org/wiki/TecDAX",
        "columns": {
            "symbol": ["Ticker symbol", "Symbol", "Kürzel"],
            "name": ["Unternehmen", "Company"],
            "sector": ["Branche", "Sector"]
        }
    },
    "CAC40": {
        "url": "https://en.wikipedia.org/wiki/CAC_40",
        "columns": {
            "symbol": ["Ticker", "Symbol"],
            "name": ["Company"],
            "sector": ["Sector"]
        }
    },
    "AEX": {
        "url": "https://en.wikipedia.org/wiki/AEX_index",
        "columns": {
            "symbol": ["Ticker", "Symbol"],
            "name": ["Company"],
            "sector": ["Sector"]
        }
    },
    "BEL20": {
        "url": "https://en.wikipedia.org/wiki/BEL_20",
        "columns": {
            "symbol": ["Ticker symbol", "Symbol"],
            "name": ["Company"],
            "sector": ["Sector", "Industry"]
        }
    },
    "SMI20": {
        "url": "https://en.wikipedia.org/wiki/Swiss_Market_Index",
        "columns": {
            "symbol": ["Ticker", "Symbol"],
            "name": ["Company"],
            "sector": ["Sector"]
        }
    },
    "OMX_STOCKHOLM": {
        "url": "https://en.wikipedia.org/wiki/OMX_Stockholm_30",
        "columns": {
            "symbol": ["Ticker symbol", "Symbol"],
            "name": ["Company", "Security"],
            "sector": ["Sector"]
        }
    },
    "OMX_HELSINKI": {
        "url": "https://en.wikipedia.org/wiki/OMX_Helsinki_25",
        "columns": {
            "symbol": ["Ticker symbol", "Symbol"],
            "name": ["Company", "Security"],
            "sector": ["Sector"]
        }
    },
    "IBOVESPA": {
        "url": "https://pt.wikipedia.org/wiki/Lista_de_companhias_citadas_no_Ibovespa",
        "columns": {
            "symbol": ["Código", "Symbol"],
            "name": ["Ação", "Empresa", "Company"],
            "sector": ["Setor", "Sector"]
        }
    },
    "NIFTY50": {
        "url": "https://en.wikipedia.org/wiki/NIFTY_50",
        "columns": {
            "symbol": ["Symbol"],
            "name": ["Company Name", "Company"],
            "sector": ["Sector"]
        }
    }
}

class YahooFinanceTickers:
    """
    Unified high-performance engine for stock tickers in Yahoo Finance format.
    Unifies pytickersymbols and yahoo-fin with offline cache fallbacks and thread-pool execution.
    """
    
    def __init__(self, cache_file_path: Optional[str] = None):
        """
        Initialize the tickers library.
        If cache_file_path is not specified, uses the pre-compiled offline json database.
        """
        if not cache_file_path:
            cache_file_path = os.path.join(
                os.path.dirname(__file__), "data", "cached_indices.json"
            )
            
        self.cache_file_path = cache_file_path
        self._cached_data: Dict[str, Any] = {}
        self._load_cache()
        
    def _load_cache(self) -> None:
        """Load data from local JSON database."""
        if os.path.exists(self.cache_file_path):
            try:
                with open(self.cache_file_path, "r", encoding="utf-8") as f:
                    self._cached_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read cached database: {e}")
                self._cached_data = {}
        else:
            logger.warning(f"Cache file not found at: {self.cache_file_path}")
            self._cached_data = {}
            
    def get_available_indices(self) -> List[str]:
        """
        Return standard identifiers for all supported indices.
        """
        # Return unique set of indices from scraping config and cache keys
        all_keys = set(INDEX_SCRAPE_CONFIG.keys()) | set(self._cached_data.keys())
        return sorted(list(all_keys))
        
    def get_tickers(self, index_name: str, force_scrape: bool = False) -> List[str]:
        """
        Get tickers in Yahoo Finance format for a given index.
        By default, loads from the optimized offline database. Set `force_scrape=True` to fetch live data.
        """
        index_name = index_name.upper().strip()
        
        if force_scrape:
            try:
                companies = self.scrape_index(index_name)
                tickers = [c["ticker"] for c in companies if c.get("ticker")]
                return sorted(list(set(tickers)))
            except Exception as e:
                logger.error(f"Live scrape failed for index {index_name}. Falling back to cache. Error: {e}")
                
        # Cache Lookup
        if index_name in self._cached_data:
            companies = self._cached_data[index_name].get("companies", [])
            tickers = []
            for c in companies:
                if c.get("ticker"):
                    tickers.append(c["ticker"])
                # Add any alternate tickers
                if c.get("other_tickers"):
                    tickers.extend(c["other_tickers"])
            return sorted(list(set(tickers)))
            
        # Fallback for Nifty Bank (hardcoded from yahoo-fin as there is no wiki table)
        if index_name == "NIFTYBANK":
            nb_tickers = ["AXISBANK.NS", "KOTAKBANK.NS", "HDFCBANK.NS", "SBIN.NS", "BANKBARODA.NS", 
                          "INDUSINDBK.NS", "PNB.NS", "IDFCFIRSTB.NS", "ICICIBANK.NS", "RBLBANK.NS", 
                          "FEDERALBNK.NS", "BANDHANBNK.NS"]
            return sorted(nb_tickers)
            
        raise ValueError(f"Index code '{index_name}' is not recognized or cached. Available indices: {self.get_available_indices()}")

    def get_metadata(self, index_name: str, force_scrape: bool = False) -> List[Dict[str, Any]]:
        """
        Get complete enriched company records for an index.
        Returns a list of dictionaries with 'name', 'ticker', 'sector', 'industry', 'isin', 'country'.
        """
        index_name = index_name.upper().strip()
        
        if force_scrape:
            try:
                return self.scrape_index(index_name)
            except Exception as e:
                logger.error(f"Live metadata scrape failed for index {index_name}. Falling back to cache. Error: {e}")
                
        if index_name in self._cached_data:
            return self._cached_data[index_name].get("companies", [])
            
        if index_name == "NIFTYBANK":
            nb_tickers = self.get_tickers("NIFTYBANK")
            return [
                {
                    "name": ticker.split('.')[0],
                    "ticker": ticker,
                    "sector": "Financials",
                    "industry": "Banks",
                    "country": "India"
                }
                for ticker in nb_tickers
            ]
            
        raise ValueError(f"Index code '{index_name}' is not recognized or cached.")

    def scrape_index(self, index_name: str) -> List[Dict[str, Any]]:
        """
        Perform a live scrape of a specific index from Wikipedia and apply suffix normalization.
        """
        index_name = index_name.upper().strip()
        
        if index_name not in INDEX_SCRAPE_CONFIG:
            # Special case fallback list format (e.g. NIKKEI 225 uses different table formats occasionally)
            if index_name == "NIKKEI225":
                # Fallback to cache since list format parsing can be brittle
                if index_name in self._cached_data:
                    return self._cached_data[index_name].get("companies", [])
            raise ValueError(f"Scraping configuration not defined for: {index_name}")
            
        cfg = INDEX_SCRAPE_CONFIG[index_name]
        
        raw_companies = parse_wikipedia_table(
            url=cfg["url"],
            column_mapping=cfg["columns"]
        )
        
        # Normalize and enrich
        normalized_companies = []
        for company in raw_companies:
            raw_sym = company.get("raw_symbol", "")
            if not raw_sym:
                continue
                
            ticker = normalize_ticker(raw_sym, index_code=index_name)
            
            comp_record = {
                "name": company.get("name", ""),
                "ticker": ticker,
                "sector": company.get("sector"),
                "industry": company.get("sector"), # default industry to sector
                "isin": company.get("isin"),
                "country": company.get("country") or self._guess_country(index_name)
            }
            normalized_companies.append(comp_record)
            
        return normalized_companies

    def scrape_all_indices(self, use_threads: bool = True, max_workers: int = 8) -> Dict[str, List[Dict[str, Any]]]:
        """
        Live scrape all supported indices concurrently using a ThreadPoolExecutor.
        Extremely fast, ideal for server sync scripts.
        """
        results = {}
        indices_to_scrape = list(INDEX_SCRAPE_CONFIG.keys())
        
        if use_threads:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_index = {
                    executor.submit(self.scrape_index, index): index 
                    for index in indices_to_scrape
                }
                for future in as_completed(future_to_index):
                    index = future_to_index[future]
                    try:
                        data = future.result()
                        results[index] = data
                        logger.info(f"Successfully scraped {index} concurrently ({len(data)} companies)")
                    except Exception as e:
                        logger.error(f"Thread failed for {index}: {e}")
                        # Fallback to cached
                        if index in self._cached_data:
                            results[index] = self._cached_data[index].get("companies", [])
        else:
            for index in indices_to_scrape:
                try:
                    data = self.scrape_index(index)
                    results[index] = data
                except Exception as e:
                    logger.error(f"Sequential scrape failed for {index}: {e}")
                    if index in self._cached_data:
                        results[index] = self._cached_data[index].get("companies", [])
                        
        return results

    def download_nasdaq_tickers(self) -> List[str]:
        """
        Download list of active tickers currently listed on NASDAQ via ftp.nasdaqtrader.com.
        Formats symbols to Yahoo Finance format.
        """
        return self._download_ftp_symbols("nasdaqlisted.txt", col_index=0)

    def download_other_tickers(self) -> List[str]:
        """
        Download list of active tickers currently listed on other exchanges (NYSE, AMEX, ARCA)
        via ftp.nasdaqtrader.com. Formats symbols to Yahoo Finance format.
        """
        return self._download_ftp_symbols("otherlisted.txt", col_index=0)

    def _download_ftp_symbols(self, filename: str, col_index: int = 0) -> List[str]:
        """Connect to NASDAQ FTP and download symbol list."""
        ftp_host = "ftp.nasdaqtrader.com"
        ftp_dir = "SymbolDirectory"
        
        try:
            ftp = ftplib.FTP(ftp_host)
            ftp.login()
            ftp.cwd(ftp_dir)
            
            r = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", r.write)
            ftp.close()
            
            content = r.getvalue().decode("utf-8")
            lines = content.strip().splitlines()
            
            # Remove header and trailer timestamps
            if lines and "File Creation Time" in lines[-1]:
                lines.pop()
                
            tickers = []
            
            # The files are pipe-delimited (|)
            # Row 0 is header: "Symbol|Security Name|Market Category|..."
            for line in lines[1:]:
                parts = line.split("|")
                if len(parts) > col_index:
                    sym = parts[col_index].strip()
                    if sym and not sym.startswith("File"):
                        # Normalize NASDAQ class notations (e.g. BRK.B -> BRK-B)
                        normalized = normalize_ticker(sym, index_code="SP500")
                        tickers.append(normalized)
                        
            return sorted(list(set(tickers)))
        except Exception as e:
            logger.error(f"FTP Download failed for {filename}: {e}")
            return []

    def save_to_json(self, data: Any, filepath: str) -> None:
        """
        Save datasets or queries in a structured JSON file.
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved JSON to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save JSON to {filepath}: {e}")
            raise e

    def _guess_country(self, index_name: str) -> str:
        """Guess the primary country of registration for index constituents."""
        if index_name in ["SP500", "SP100", "SP600", "DOW", "NASDAQ100"]:
            return "United States"
        elif index_name in ["FTSE100", "FTSE250"]:
            return "United Kingdom"
        elif index_name in ["DAX", "MDAX", "SDAX", "TECDAX"]:
            return "Germany"
        elif index_name in ["CAC40", "CACMID60"]:
            return "France"
        elif index_name == "AEX":
            return "Netherlands"
        elif index_name == "BEL20":
            return "Belgium"
        elif index_name == "SMI20":
            return "Switzerland"
        elif index_name == "OMX_STOCKHOLM":
            return "Sweden"
        elif index_name == "OMX_HELSINKI":
            return "Finland"
        elif index_name == "NIKKEI225":
            return "Japan"
        elif index_name == "IBOVESPA":
            return "Brazil"
        elif index_name in ["NIFTY50", "NIFTYBANK"]:
            return "India"
        return "Global"
