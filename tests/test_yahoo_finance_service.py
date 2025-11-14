"""
Tests untuk Yahoo Finance Service.

Test coverage untuk fetching stock data dari Yahoo Finance API.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.models.stock_data import StockData
from src.services.yahoo_finance_service import YahooFinanceService


class TestYahooFinanceService:
    """Test suite untuk YahooFinanceService."""

    @pytest.fixture
    def service(self):
        """Create YahooFinanceService instance."""
        return YahooFinanceService()

    @pytest.fixture
    def mock_yfinance_info(self):
        """Mock yfinance info data."""
        return {
            "symbol": "BBCA.JK",
            "shortName": "Bank Central Asia Tbk",
            "longName": "PT Bank Central Asia Tbk",
            "sector": "Financial Services",
            "industry": "Banks - Regional",
            "currentPrice": 10000,
            "marketCap": 1234567890000,
            "trailingPE": 12.5,
            "priceToBook": 3.2,
            "returnOnEquity": 0.18,
            "profitMargins": 0.35,
            "debtToEquity": 45.5,
            "beta": 0.95,
            "dividendYield": 0.025,
            "trailingEps": 800,
            "operatingCashflow": 50000000000,
            "freeCashflow": 40000000000,
        }

    @pytest.fixture
    def mock_ticker(self, mock_yfinance_info):
        """Create mock yfinance Ticker object."""
        mock = MagicMock()
        mock.info = mock_yfinance_info

        # Mock earnings history
        mock.earnings_history = MagicMock()
        mock.earnings_history.empty = False

        # Mock financials for historical EPS
        mock.earnings = MagicMock()
        mock.earnings.empty = False

        return mock

    def test_get_stock_data_success(self, service, mock_ticker):
        """Test successful stock data fetching."""
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = service.get_stock_data("BBCA")

            assert result is not None
            assert isinstance(result, StockData)
            assert result.get_ticker() == "BBCA.JK"
            assert result.company_info.name == "PT Bank Central Asia Tbk"
            assert result.company_info.sector == "Financial Services"
            assert result.price.current_price == 10000
            assert result.valuation.pe_ratio == 12.5
            assert result.valuation.price_to_book == 3.2
            assert result.profitability.roe == 0.18
            assert result.leverage.debt_to_equity == 45.5
            assert result.leverage.beta == 0.95
            assert result.dividend.dividend_yield == 0.025

    def test_get_stock_data_with_normalized_ticker(self, service, mock_ticker):
        """Test fetching with various ticker formats."""
        with patch("yfinance.Ticker", return_value=mock_ticker):
            # Test without .JK suffix
            result1 = service.get_stock_data("BBCA")
            assert result1 is not None
            assert result1.get_ticker() == "BBCA.JK"

            # Test with .JK suffix already
            result2 = service.get_stock_data("BBCA.JK")
            assert result2 is not None
            assert result2.get_ticker() == "BBCA.JK"

    def test_get_stock_data_invalid_ticker(self, service):
        """Test fetching with invalid ticker."""
        mock_ticker = MagicMock()
        mock_ticker.info = {}  # Empty info

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = service.get_stock_data("INVALID")
            assert result is None

    def test_get_stock_data_api_error(self, service):
        """Test handling of API errors."""
        with patch("yfinance.Ticker", side_effect=Exception("API Error")):
            result = service.get_stock_data("BBCA")
            assert result is None

    def test_caching_mechanism(self, service, mock_ticker):
        """Test that caching works properly."""
        with patch("yfinance.Ticker", return_value=mock_ticker) as mock_yf:
            # First call should hit API
            result1 = service.get_stock_data("BBCA", use_cache=True)
            assert result1 is not None
            assert mock_yf.call_count == 1

            # Second call should use cache
            result2 = service.get_stock_data("BBCA", use_cache=True)
            assert result2 is not None
            assert mock_yf.call_count == 1  # Still 1, didn't call API again

            # Same object from cache
            assert result1 is result2

    def test_cache_bypass(self, service, mock_ticker):
        """Test that cache can be bypassed."""
        with patch("yfinance.Ticker", return_value=mock_ticker) as mock_yf:
            # First call
            result1 = service.get_stock_data("BBCA", use_cache=False)
            assert mock_yf.call_count == 1

            # Second call with use_cache=False should hit API again
            result2 = service.get_stock_data("BBCA", use_cache=False)
            assert mock_yf.call_count == 2

    def test_missing_optional_fields(self, service):
        """Test handling of missing optional fields."""
        # Mock with minimal required fields only
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "symbol": "TEST.JK",
            "shortName": "Test Company",
            "currentPrice": 1000,
            # Missing many optional fields
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = service.get_stock_data("TEST")

            assert result is not None
            assert result.company_info.name == "Test Company"
            assert result.price.current_price == 1000
            # Optional fields should be None
            assert result.valuation.pe_ratio is None
            assert result.profitability.roe is None

    def test_negative_values_handling(self, service):
        """Test handling of negative financial values."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "symbol": "LOSS.JK",
            "shortName": "Loss Maker",
            "currentPrice": 500,
            "trailingEps": -100,  # Negative EPS
            "returnOnEquity": -0.05,  # Negative ROE
            "freeCashflow": -1000000,  # Negative FCF
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = service.get_stock_data("LOSS")

            assert result is not None
            assert result.profitability.eps == -100
            assert result.profitability.roe == -0.05
            assert result.cash_flow.free_cash_flow == -1000000

    def test_multiple_stocks_caching(self, service, mock_ticker):
        """Test caching with multiple different stocks."""
        with patch("yfinance.Ticker", return_value=mock_ticker) as mock_yf:
            # Fetch multiple different stocks
            result1 = service.get_stock_data("BBCA")
            result2 = service.get_stock_data("BMRI")
            result3 = service.get_stock_data("BBCA")  # Should use cache

            assert result1 is not None
            assert result2 is not None
            assert result3 is not None

            # Should have called API twice (BBCA and BMRI), third call uses cache
            assert mock_yf.call_count == 2

            # Verify cache hit for BBCA
            assert "BBCA.JK" in service.cache
            assert "BMRI.JK" in service.cache

    def test_get_eps_history_with_earnings(self, service):
        """Test _get_eps_history dengan earnings data."""
        import pandas as pd

        mock_ticker = MagicMock()

        # Mock financials - harus tidak None dan tidak empty
        mock_financials = pd.DataFrame(
            {"Revenue": [1000000, 1100000, 1200000, 1300000, 1400000]},
            index=[pd.Timestamp(f"{year}-01-01") for year in range(2020, 2025)],
        )

        # Mock earnings DataFrame
        mock_earnings = pd.DataFrame(
            {"Earnings": [800, 850, 900, 950, 1000]},
            index=[pd.Timestamp(f"{year}-01-01") for year in range(2020, 2025)],
        )

        mock_ticker.financials = mock_financials
        mock_ticker.earnings = mock_earnings

        eps_history = service._get_eps_history(mock_ticker)

        assert len(eps_history) > 0
        assert all(isinstance(year, int) for year in eps_history.keys())

    def test_get_eps_history_with_timestamp(self, service):
        """Test _get_eps_history dengan timestamp index."""
        import pandas as pd
        from datetime import datetime

        mock_ticker = MagicMock()

        # Mock financials - harus tidak None dan tidak empty
        mock_financials = pd.DataFrame(
            {"Revenue": [1000000, 1100000]},
            index=[datetime(2023, 1, 1), datetime(2024, 1, 1)],
        )

        mock_earnings = pd.DataFrame(
            {"Earnings": [800, 850]}, index=[datetime(2023, 1, 1), datetime(2024, 1, 1)]
        )

        mock_ticker.financials = mock_financials
        mock_ticker.earnings = mock_earnings

        eps_history = service._get_eps_history(mock_ticker)
        assert len(eps_history) > 0

    def test_get_eps_history_with_string_year(self, service):
        """Test _get_eps_history dengan string year."""
        mock_ticker = MagicMock()

        import pandas as pd

        mock_earnings = pd.DataFrame(
            {"Earnings": [800]}, index=[pd.Index(["2024-01-01"])]
        )

        mock_ticker.earnings = mock_earnings

        eps_history = service._get_eps_history(mock_ticker)
        # Should handle gracefully
        assert isinstance(eps_history, dict)

    def test_get_eps_history_error_handling(self, service):
        """Test _get_eps_history error handling."""
        mock_ticker = MagicMock()
        mock_ticker.earnings = None
        mock_ticker.financials = None
        mock_ticker.info = {}  # No trailing EPS

        eps_history = service._get_eps_history(mock_ticker)
        assert eps_history == {}

    def test_get_eps_history_exception(self, service):
        """Test _get_eps_history dengan exception."""
        mock_ticker = MagicMock()
        mock_ticker.earnings.side_effect = Exception("Error")
        mock_ticker.financials = None
        mock_ticker.info = {}  # No trailing EPS

        eps_history = service._get_eps_history(mock_ticker)
        assert eps_history == {}

    def test_calculate_data_quality_zero_fields(self, service):
        """Test _calculate_data_quality dengan zero fields."""
        from src.models.stock_data import (
            ValuationMetrics,
            ProfitabilityMetrics,
            CashFlowMetrics,
            LeverageMetrics,
            DividendMetrics,
        )

        # All None values
        valuation = ValuationMetrics()
        profitability = ProfitabilityMetrics()
        cash_flow = CashFlowMetrics()
        leverage = LeverageMetrics()
        dividend = DividendMetrics()

        quality = service._calculate_data_quality(
            valuation, profitability, cash_flow, leverage, dividend
        )
        assert quality == 0.0

    def test_clear_cache(self, service, mock_ticker):
        """Test clear_cache method."""
        with patch("yfinance.Ticker", return_value=mock_ticker):
            service.get_stock_data("BBCA")
            assert len(service.cache) > 0

            service.clear_cache()
            assert len(service.cache) == 0

    def test_get_multiple_stocks(self, service, mock_ticker):
        """Test get_multiple_stocks method."""
        with patch("yfinance.Ticker", return_value=mock_ticker):
            results = service.get_multiple_stocks(["BBCA", "BMRI"])

            assert "BBCA" in results or "BBCA.JK" in results
            assert len(results) == 2

    def test_get_multiple_stocks_with_cache(self, service, mock_ticker):
        """Test get_multiple_stocks dengan cache."""
        with patch("yfinance.Ticker", return_value=mock_ticker) as mock_yf:
            # First call
            results1 = service.get_multiple_stocks(["BBCA"], use_cache=True)
            assert mock_yf.call_count == 1

            # Second call with cache
            results2 = service.get_multiple_stocks(["BBCA"], use_cache=True)
            assert mock_yf.call_count == 1  # Should use cache
