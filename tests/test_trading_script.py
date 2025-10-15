import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime
import sys

# Add the script's directory to the Python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Scripts and CSV Files"))
)

from Trading_Script import (
    get_portfolio_and_cash,
    save_portfolio_and_cash,
    process_portfolio,
    log_sell,
    log_manual_buy,
    log_manual_sell,
)


def create_mock_history(price: float) -> pd.DataFrame:
    """Create a mock DataFrame for yfinance history."""
    return pd.DataFrame({"Close": [price]})


class TestTradingScript(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory and portfolio file for testing."""
        self.test_dir = "test_data"
        os.makedirs(self.test_dir, exist_ok=True)
        self.portfolio_path = os.path.join(self.test_dir, "test_portfolio.csv")

    def tearDown(self):
        """Clean up the temporary directory and files after testing."""
        if os.path.exists(self.portfolio_path):
            os.remove(self.portfolio_path)
        os.rmdir(self.test_dir)

    def test_get_portfolio_and_cash_no_file(self):
        """Test loading portfolio when the file does not exist."""
        portfolio, cash = get_portfolio_and_cash("non_existent_file.csv")
        self.assertTrue(portfolio.empty)
        self.assertEqual(cash, 100.0)

    def test_get_portfolio_and_cash_with_file(self):
        """Test loading portfolio from an existing CSV file."""
        data = {
            "ticker": ["ABEO", "IINN"],
            "shares": [4, 16],
            "stop_loss": [4.90, 1.10],
            "buy_price": [5.77, 1.50],
            "cost_basis": [23.08, 24.48],
            "cash": [31.58, 31.58],
        }
        df = pd.DataFrame(data)
        df.to_csv(self.portfolio_path, index=False)
        portfolio, cash = get_portfolio_and_cash(self.portfolio_path)
        self.assertEqual(len(portfolio), 2)
        self.assertEqual(cash, 31.58)

    def test_save_portfolio_and_cash(self):
        """Test saving the portfolio and cash to a CSV file."""
        data = {
            "ticker": ["ABEO"],
            "shares": [4],
            "stop_loss": [4.90],
            "buy_price": [5.77],
            "cost_basis": [23.08],
        }
        portfolio = pd.DataFrame(data)
        cash = 50.0
        save_portfolio_and_cash(portfolio, cash, self.portfolio_path)
        df = pd.read_csv(self.portfolio_path)
        self.assertEqual(df["cash"][0], 50.0)
        self.assertEqual(df["ticker"][0], "ABEO")

    @patch("Trading_Script.yf.Ticker")
    @patch("builtins.input", side_effect=[""])
    def test_process_portfolio_hold(self, mock_input, mock_ticker):
        """Test the process_portfolio function with a HOLD action."""
        mock_ticker.return_value.history.return_value = create_mock_history(6.00)

        portfolio = pd.DataFrame(
            [
                {
                    "ticker": "ABEO",
                    "shares": 4,
                    "stop_loss": 4.90,
                    "buy_price": 5.77,
                    "cost_basis": 23.08,
                }
            ]
        )
        starting_cash = 31.58
        updated_portfolio, cash = process_portfolio(portfolio, starting_cash)
        self.assertEqual(len(updated_portfolio), 1)
        self.assertAlmostEqual(cash, 31.58, places=2)

    @patch("Trading_Script.yf.Ticker")
    @patch("builtins.input", side_effect=[""])
    def test_process_portfolio_sell(self, mock_input, mock_ticker):
        """Test the process_portfolio function with a SELL action (stop-loss)."""
        mock_ticker.return_value.history.return_value = create_mock_history(4.50)

        portfolio = pd.DataFrame(
            [
                {
                    "ticker": "ABEO",
                    "shares": 4,
                    "stop_loss": 4.90,
                    "buy_price": 5.77,
                    "cost_basis": 23.08,
                }
            ]
        )
        starting_cash = 31.58
        with patch("Trading_Script.log_sell") as mock_log_sell:
            mock_log_sell.return_value = pd.DataFrame(
                columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"]
            )
            updated_portfolio, cash = process_portfolio(portfolio, starting_cash)
            mock_log_sell.assert_called_once()
            self.assertEqual(len(updated_portfolio), 0)
            self.assertAlmostEqual(cash, 31.58 + (4.50 * 4), places=2)

    def test_log_sell(self):
        """Test the log_sell function."""
        portfolio = pd.DataFrame([{"ticker": "ABEO", "shares": 4}])
        updated_portfolio = log_sell("ABEO", 4, 4.50, 5.77, -5.08, portfolio)
        self.assertEqual(len(updated_portfolio), 0)

    @patch("Trading_Script.yf.download")
    @patch("builtins.input", side_effect=[""])
    def test_log_manual_buy(self, mock_input, mock_download):
        """Test the log_manual_buy function."""
        mock_download.return_value = create_mock_history(10.0)
        portfolio = pd.DataFrame(
            columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"]
        )
        cash, updated_portfolio = log_manual_buy(
            10.0, 10, "TEST", 9.0, 1000.0, portfolio
        )
        self.assertEqual(len(updated_portfolio), 1)
        self.assertEqual(updated_portfolio["ticker"][0], "TEST")
        self.assertEqual(cash, 900.0)

    @patch("builtins.input", side_effect=["Test sell", ""])
    def test_log_manual_sell(self, mock_input):
        """Test the log_manual_sell function."""
        portfolio = pd.DataFrame(
            [
                {
                    "ticker": "ABEO",
                    "shares": 10,
                    "stop_loss": 4.90,
                    "buy_price": 5.77,
                    "cost_basis": 57.70,
                }
            ]
        )
        cash, updated_portfolio = log_manual_sell(6.0, 5, "ABEO", 100.0, portfolio)
        self.assertEqual(updated_portfolio["shares"].iloc[0], 5)
        self.assertEqual(cash, 130.0)


if __name__ == "__main__":
    unittest.main()
