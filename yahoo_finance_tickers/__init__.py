"""
Yahoo Finance Tickers Unified Library

A high-performance library that unifies the indexing and mapping capabilities of pytickersymbols 
with the robust scraping/FTP interfaces of yahoo-fin to serve clean tickers in Yahoo Finance format.
"""

from yahoo_finance_tickers.tickers import YahooFinanceTickers
from yahoo_finance_tickers.utils import normalize_ticker

__version__ = "0.1.0"
__all__ = ["YahooFinanceTickers", "normalize_ticker"]
