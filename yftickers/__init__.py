"""
yftickers Unified Library

A high-performance library that unifies the indexing and mapping capabilities of pytickersymbols 
with the robust scraping/FTP interfaces of yahoo-fin to serve clean tickers in Yahoo Finance format,
while providing high-speed and optimized yfinance-compatible data client capabilities.
"""

from yftickers.tickers import YahooFinanceTickers
from yftickers.utils import normalize_ticker, register_exchange_suffix
from yftickers.ticker import Ticker
from yftickers.multi import download

__version__ = "0.2.0"
__all__ = [
    "YahooFinanceTickers",
    "normalize_ticker",
    "register_exchange_suffix",
    "Ticker",
    "download"
]
