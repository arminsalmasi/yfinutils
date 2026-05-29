import os
import json
import unittest
from unittest.mock import patch, MagicMock
import tempfile

from yftickers import YahooFinanceTickers, normalize_ticker
from yftickers.utils import INDEX_SUFFIX_MAP

class TestYahooFinanceTickers(unittest.TestCase):
    
    def setUp(self):
        # We can test with the packaged cache since it is copied
        self.engine = YahooFinanceTickers()
        
    def test_normalize_ticker_us(self):
        # US Equity classes
        self.assertEqual(normalize_ticker("BRK.B", "SP500"), "BRK-B")
        self.assertEqual(normalize_ticker("BF/B", "SP500"), "BF-B")
        self.assertEqual(normalize_ticker("AAPL", "SP500"), "AAPL")
        self.assertEqual(normalize_ticker("AAPL", "NASDAQ100"), "AAPL")
        
    def test_normalize_ticker_international(self):
        # Suffix matching
        self.assertEqual(normalize_ticker("SHEL", "FTSE100"), "SHEL.L")
        self.assertEqual(normalize_ticker("SHEL.L", "FTSE100"), "SHEL.L") # no double suffix
        self.assertEqual(normalize_ticker("SAP", "DAX"), "SAP.DE")
        self.assertEqual(normalize_ticker("NESN", "SMI20"), "NESN.SW")
        self.assertEqual(normalize_ticker("PETR4", "IBOVESPA"), "PETR4.SA")
        self.assertEqual(normalize_ticker("RELIANCE", "NIFTY50"), "RELIANCE.NS")
        
    def test_get_available_indices(self):
        indices = self.engine.get_available_indices()
        self.assertIn("SP500", indices)
        self.assertIn("DAX", indices)
        self.assertIn("FTSE100", indices)
        self.assertIn("NASDAQ100", indices)
        self.assertTrue(len(indices) >= 15)
        
    def test_get_tickers_cached(self):
        # S&P 500 cached tickers
        sp500_tickers = self.engine.get_tickers("SP500")
        self.assertTrue(len(sp500_tickers) > 100)
        self.assertIn("AAPL", sp500_tickers)
        
        # Verify international tickers have the proper suffix
        dax_tickers = self.engine.get_tickers("DAX")
        self.assertTrue(len(dax_tickers) >= 30)
        # Check suffix appended correctly
        self.assertTrue(any(t.endswith(".DE") for t in dax_tickers))
        
    def test_get_metadata_cached(self):
        sp500_meta = self.engine.get_metadata("SP500")
        self.assertTrue(len(sp500_meta) > 100)
        first_comp = sp500_meta[0]
        self.assertIn("name", first_comp)
        self.assertIn("ticker", first_comp)
        self.assertIn("sector", first_comp)
        self.assertEqual(first_comp["country"], "United States")
        
    def test_save_to_json(self):
        dax_tickers = self.engine.get_tickers("DAX")
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "dax_tickers.json")
            self.engine.save_to_json(dax_tickers, filepath)
            
            self.assertTrue(os.path.exists(filepath))
            with open(filepath, "r") as f:
                loaded = json.load(f)
            self.assertEqual(loaded, dax_tickers)
            
    @patch("ftplib.FTP")
    def test_download_nasdaq_tickers_mock(self, mock_ftp_class):
        # Mock FTP connection and file download
        mock_ftp_inst = MagicMock()
        mock_ftp_class.return_value = mock_ftp_inst
        
        # Define mock file bytes downloaded
        mock_data = b"Symbol|Security Name\nAAPL|Apple Inc.\nMSFT|Microsoft Corp.\nBRK.B|Berkshire Hathaway\nFile Creation Time: 2026-05-29"
        
        def mock_retr(cmd, callback):
            callback(mock_data)
            
        mock_ftp_inst.retrbinary.side_effect = mock_retr
        
        tickers = self.engine.download_nasdaq_tickers()
        
        mock_ftp_class.assert_called_once_with("ftp.nasdaqtrader.com")
        mock_ftp_inst.login.assert_called_once()
        mock_ftp_inst.cwd.assert_called_once_with("SymbolDirectory")
        mock_ftp_inst.close.assert_called_once()
        
        self.assertEqual(tickers, ["AAPL", "BRK-B", "MSFT"])

    @patch("yftickers.tickers.parse_wikipedia_table")
    def test_scrape_index_mock(self, mock_parse):
        # Mock parser
        mock_parse.return_value = [
            {"name": "AstraZeneca", "raw_symbol": "AZN", "sector": "Healthcare"},
            {"name": "BP", "raw_symbol": "BP", "sector": "Energy"}
        ]
        
        ftse_meta = self.engine.scrape_index("FTSE100")
        
        mock_parse.assert_called_once()
        self.assertEqual(len(ftse_meta), 2)
        self.assertEqual(ftse_meta[0]["ticker"], "AZN.L")
        self.assertEqual(ftse_meta[0]["country"], "United Kingdom")
        self.assertEqual(ftse_meta[1]["ticker"], "BP.L")
        
    @patch("yftickers.tickers.YahooFinanceTickers.scrape_index")
    def test_scrape_all_indices_concurrent(self, mock_scrape):
        mock_scrape.side_effect = lambda index: [{"name": "Mock", "ticker": f"MOCK.{index}"}]
        
        results = self.engine.scrape_all_indices(use_threads=True, max_workers=4)
        
        # Verify all index configs were processed
        from yftickers.tickers import INDEX_SCRAPE_CONFIG
        self.assertEqual(len(results), len(INDEX_SCRAPE_CONFIG))
        self.assertIn("SP500", results)
        self.assertIn("DAX", results)
        self.assertEqual(results["DAX"], [{"name": "Mock", "ticker": "MOCK.DAX"}])

    def test_dynamic_suffix_registration(self):
        # Register a new custom suffix
        self.engine.register_suffix("MY_NEW_EXCHANGE", ".NX")
        self.assertEqual(normalize_ticker("TEST", "MY_NEW_EXCHANGE"), "TEST.NX")
        
        # Test standard newly added global suffix (e.g. Stockholm .ST, Canada .TO, Australia .AX)
        self.assertEqual(normalize_ticker("ATCO-A", "STOCKHOLM"), "ATCO-A.ST")
        self.assertEqual(normalize_ticker("BHP", "AUSTRALIA"), "BHP.AX")
        self.assertEqual(normalize_ticker("SHOP", "TORONTO"), "SHOP.TO")

    @patch("requests.get")
    def test_search_tickers_mock(self, mock_get):
        # Define mock search response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "quotes": [
                {"symbol": "VOLV-B.ST", "longname": "Volvo AB", "exchange": "STO", "exchDisp": "Stockholm", "quoteType": "EQUITY", "typeDisp": "Equity"},
                {"symbol": "AAPL", "longname": "Apple Inc.", "exchange": "NMS", "exchDisp": "NASDAQ", "quoteType": "EQUITY", "typeDisp": "Equity"}
            ]
        }
        mock_get.return_value = mock_response
        
        results = self.engine.search_tickers("Volvo")
        
        mock_get.assert_called_once()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["symbol"], "VOLV-B.ST")
        self.assertEqual(results[0]["name"], "Volvo AB")
        self.assertEqual(results[0]["exchange_display"], "Stockholm")
        self.assertEqual(results[1]["symbol"], "AAPL")

if __name__ == "__main__":
    unittest.main()
