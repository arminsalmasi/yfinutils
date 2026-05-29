import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from yfinutils import YahooFinanceTickers
# Initialize the yfinutils engine
yft = YahooFinanceTickers()
# 1. Extract Stockholm (OMX 30) tickers
stockholm_tickers = yft.get_tickers("OMX_STOCKHOLM")
print(f"Loaded {len(stockholm_tickers)} Stockholm tickers:")
print(stockholm_tickers)
# 2. Extract Stockholm company metadata (includes names, sectors, ISINs, etc.)
stockholm_metadata = yft.get_metadata("OMX_STOCKHOLM")
print(f"\nMetadata Example (First Company):")
print(stockholm_metadata[0])
# 3. Save the tickers to a JSON file (in Yahoo Finance format)
yft.save_to_json(stockholm_tickers, "stockholm_tickers.json")
print("\n✓ Saved Stockholm tickers list to 'stockholm_tickers.json'")