import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from yftickers import Ticker, download
from yftickers.session import YahooSessionManager, yahoo_session

class TestHistoricalData(unittest.TestCase):
    
    def test_session_singleton(self):
        # Verify YahooSessionManager is a singleton
        session1 = YahooSessionManager()
        session2 = YahooSessionManager()
        self.assertIs(session1, session2)
        self.assertIs(session1, yahoo_session)

    @patch("yftickers.session.YahooSessionManager.get_cookie_and_crumb")
    @patch("requests.Session.get")
    def test_ticker_history_parsing(self, mock_get, mock_cookie_crumb):
        # 1. Mock session crumb and response
        mock_cookie_crumb.return_value = (None, "mock_crumb")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "USD",
                            "symbol": "AAPL",
                            "exchangeName": "NMS",
                            "instrumentType": "EQUITY",
                            "exchangeTimezoneName": "America/New_York",
                        },
                        "timestamp": [1683552600, 1683639000],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [173.85, 173.05],
                                    "high": [174.59, 173.54],
                                    "low": [172.55, 171.58],
                                    "close": [173.5, 171.77],
                                    "volume": [55962800, 45326900],
                                }
                            ],
                            "adjclose": [
                                {
                                    "adjclose": [173.0583, 171.3323]
                                }
                            ]
                        },
                        "events": {
                            "dividends": {
                                "1683639000": { "amount": 0.24, "date": 1683639000 }
                            },
                            "splits": {
                                "1683552600": { "numerator": 4, "denominator": 1, "date": 1683552600 }
                            }
                        }
                    }
                ],
                "error": None
            }
        }
        mock_get.return_value = mock_resp
        
        # 2. Test without auto_adjust
        ticker = Ticker("AAPL")
        df = ticker.history(period="1mo", auto_adjust=False, actions=True)
        
        # Verify columns
        self.assertIn("Open", df.columns)
        self.assertIn("Adj Close", df.columns)
        self.assertIn("Dividends", df.columns)
        self.assertIn("Stock Splits", df.columns)
        
        # Verify shape
        self.assertEqual(len(df), 2)
        
        # Verify values
        self.assertEqual(df["Close"].iloc[0], 173.5)
        self.assertEqual(df["Adj Close"].iloc[0], 173.0583)
        self.assertEqual(df["Dividends"].iloc[1], 0.24)
        self.assertEqual(df["Stock Splits"].iloc[0], 4.0)
        
        # Verify index is localized to America/New_York
        self.assertEqual(str(df.index.tz), "America/New_York")

    @patch("yftickers.session.YahooSessionManager.get_cookie_and_crumb")
    @patch("requests.Session.get")
    def test_ticker_history_auto_adjust(self, mock_get, mock_cookie_crumb):
        # Mock response
        mock_cookie_crumb.return_value = (None, "mock_crumb")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "exchangeTimezoneName": "UTC",
                        },
                        "timestamp": [1683552600],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [10.0],
                                    "high": [12.0],
                                    "low": [8.0],
                                    "close": [10.0],
                                    "volume": [1000],
                                }
                            ],
                            "adjclose": [
                                {
                                    "adjclose": [5.0]  # Ratio of 0.5
                                }
                            ]
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_resp
        
        ticker = Ticker("TEST")
        df = ticker.history(period="1mo", auto_adjust=True)
        
        # Close column should equal Adj Close, Open should be adjusted
        self.assertNotIn("Adj Close", df.columns)
        self.assertEqual(df["Close"].iloc[0], 5.0)
        self.assertEqual(df["Open"].iloc[0], 5.0)
        self.assertEqual(df["High"].iloc[0], 6.0)
        self.assertEqual(df["Low"].iloc[0], 4.0)

    @patch("yftickers.session.YahooSessionManager.get_cookie_and_crumb")
    @patch("requests.Session.get")
    def test_ticker_info(self, mock_get, mock_cookie_crumb):
        mock_cookie_crumb.return_value = (None, "mock_crumb")
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "quoteResponse": {
                "result": [
                    {
                        "symbol": "AAPL",
                        "longName": "Apple Inc.",
                        "regularMarketPrice": 175.0,
                    }
                ]
            }
        }
        mock_get.return_value = mock_resp
        
        ticker = Ticker("AAPL")
        info = ticker.info
        
        self.assertEqual(info["longName"], "Apple Inc.")
        self.assertEqual(info["regularMarketPrice"], 175.0)

    @patch("yftickers.ticker.Ticker.history")
    def test_download_multi_tickers(self, mock_history):
        # Mock individual history downloads
        df_aapl = pd.DataFrame(
            {"Open": [10.0], "Close": [11.0]},
            index=pd.to_datetime(["2026-05-29"])
        )
        df_msft = pd.DataFrame(
            {"Open": [20.0], "Close": [22.0]},
            index=pd.to_datetime(["2026-05-29"])
        )
        
        def mock_hist(*args, **kwargs):
            # args[0] is not present since we patched Ticker.history method directly on class
            # Wait, self inside patched method. We can inspect the self instance.
            # But simpler: check the ticker symbol of the Ticker instance inside the mock.
            # Let's inspect the mock_history call or just return data based on self.ticker
            # Since self is passed as the first arg in instance methods:
            ticker_inst = mock_history.call_args_list[len(results_to_return)][0][0]
            # Wait, no. Let's make a side_effect function that handles this dynamically.
            # Since we patched Ticker.history, mock_history is a MagicMock which replaces Ticker.history.
            # When Ticker("AAPL").history() is called, it calls Ticker.history(self, ...) where self is the Ticker instance.
            pass
            
        # Instead of patching Ticker.history on class level, let's patch Ticker's constructor or instance methods, or patch execute_request!
        # Actually, let's patch execute_request in download.
        # But wait, download constructs Ticker.history. If we mock execute_request in YahooSessionManager:
        # We can return different chart data for different URLs! That is even more realistic.
        
    @patch("requests.Session.get")
    @patch("yftickers.session.YahooSessionManager.get_cookie_and_crumb")
    def test_download_multi_tickers_via_request(self, mock_cookie_crumb, mock_get):
        mock_cookie_crumb.return_value = (None, "mock_crumb")
        
        def mock_get_side_effect(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            if "AAPL" in url:
                resp.json.return_value = {
                    "chart": {
                        "result": [
                            {
                                "meta": {"exchangeTimezoneName": "UTC"},
                                "timestamp": [1683552600],
                                "indicators": {
                                    "quote": [{"open": [100.0], "close": [105.0]}],
                                    "adjclose": [{"adjclose": [105.0]}]
                                }
                            }
                        ]
                    }
                }
            elif "MSFT" in url:
                resp.json.return_value = {
                    "chart": {
                        "result": [
                            {
                                "meta": {"exchangeTimezoneName": "UTC"},
                                "timestamp": [1683552600],
                                "indicators": {
                                    "quote": [{"open": [300.0], "close": [310.0]}],
                                    "adjclose": [{"adjclose": [310.0]}]
                                }
                            }
                        ]
                    }
                }
            return resp
            
        mock_get.side_effect = mock_get_side_effect
        
        # Test download
        df = download("AAPL MSFT", period="1mo", progress=False, threads=False)
        
        # Verify MultiIndex columns structure
        self.assertIn("Close", df.columns.levels[0])
        self.assertIn("AAPL", df.columns.levels[1])
        self.assertIn("MSFT", df.columns.levels[1])
        
        # Verify values
        self.assertEqual(df[("Close", "AAPL")].iloc[0], 105.0)
        self.assertEqual(df[("Close", "MSFT")].iloc[0], 310.0)

if __name__ == "__main__":
    unittest.main()
