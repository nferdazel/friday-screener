"""
Service untuk mengambil data saham dari Yahoo Finance.

Service ini menggunakan yfinance library untuk fetch data fundamental,
harga, dan informasi lainnya dari Yahoo Finance API.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Optional
import warnings

import yfinance as yf

from src.models.stock_data import (
    CashFlowMetrics,
    CompanyInfo,
    DividendMetrics,
    LeverageMetrics,
    PriceMetrics,
    ProfitabilityMetrics,
    StockData,
    ValuationMetrics,
)
from src.utils.helpers import normalize_ticker, safe_float, safe_int
from src.utils.logger import get_logger

# Suppress yfinance deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.simplefilter("ignore")

logger = get_logger(__name__)


class YahooFinanceService:
    """Service untuk fetch data dari Yahoo Finance."""

    def __init__(self):
        """Initialize Yahoo Finance service."""
        self.cache: Dict[str, StockData] = {}

    def get_stock_data(
        self, ticker: str, use_cache: bool = True
    ) -> Optional[StockData]:
        """
        Fetch comprehensive stock data dari Yahoo Finance.

        Args:
            ticker: Stock ticker symbol (akan dinormalisasi otomatis)
            use_cache: Whether to use cached data if available

        Returns:
            StockData object atau None jika fetch gagal
        """
        normalized_ticker = normalize_ticker(ticker)

        # Check cache
        if use_cache and normalized_ticker in self.cache:
            logger.info(f"Using cached data for {normalized_ticker}")
            return self.cache[normalized_ticker]

        logger.info(f"Fetching data for {normalized_ticker} from Yahoo Finance...")

        try:
            # Create yfinance Ticker object
            stock = yf.Ticker(normalized_ticker)

            # Fetch all data
            info = stock.info
            if not info or "symbol" not in info:
                logger.error(f"Failed to fetch data for {normalized_ticker}")
                return None

            # Build StockData object
            stock_data = self._build_stock_data(stock, info, normalized_ticker)

            # Cache the result
            self.cache[normalized_ticker] = stock_data

            logger.info(f"Successfully fetched data for {normalized_ticker}")
            return stock_data

        except Exception as e:
            logger.error(f"Error fetching data for {normalized_ticker}: {str(e)}")
            return None

    def _build_stock_data(self, stock: yf.Ticker, info: dict, ticker: str) -> StockData:
        """
        Build StockData object dari yfinance data.

        Args:
            stock: yfinance Ticker object
            info: Info dictionary dari yfinance
            ticker: Ticker symbol

        Returns:
            StockData object
        """
        # Company Info
        company_info = CompanyInfo(
            ticker=ticker,
            name=info.get("longName", info.get("shortName", ticker)),
            sector=info.get("sector"),
            industry=info.get("industry"),
            description=info.get("longBusinessSummary"),
            website=info.get("website"),
            country=info.get("country"),
        )

        # Valuation Metrics
        valuation = ValuationMetrics(
            market_cap=safe_float(info.get("marketCap")),
            enterprise_value=safe_float(info.get("enterpriseValue")),
            pe_ratio=safe_float(info.get("trailingPE")),
            forward_pe=safe_float(info.get("forwardPE")),
            peg_ratio=safe_float(info.get("pegRatio")),
            price_to_book=safe_float(info.get("priceToBook")),
            price_to_sales=safe_float(info.get("priceToSalesTrailing12Months")),
            shares_outstanding=safe_float(info.get("sharesOutstanding")),
        )

        # Profitability Metrics
        profitability = ProfitabilityMetrics(
            revenue=safe_float(info.get("totalRevenue")),
            gross_profit=safe_float(info.get("grossProfits")),
            operating_income=safe_float(info.get("operatingIncome")),
            net_income=safe_float(info.get("netIncomeToCommon")),
            eps=safe_float(info.get("trailingEps")),
            gross_margin=safe_float(info.get("grossMargins")),
            operating_margin=safe_float(info.get("operatingMargins")),
            profit_margin=safe_float(info.get("profitMargins")),
            roe=safe_float(info.get("returnOnEquity")),
            roa=safe_float(info.get("returnOnAssets")),
            eps_history=self._get_eps_history(stock),
        )

        # Cash Flow Metrics
        cash_flow = CashFlowMetrics(
            operating_cash_flow=safe_float(info.get("operatingCashflow")),
            free_cash_flow=safe_float(info.get("freeCashflow")),
            levered_free_cash_flow=safe_float(info.get("leveredFreeCashflow")),
        )

        # Leverage Metrics
        leverage = LeverageMetrics(
            total_debt=safe_float(info.get("totalDebt")),
            total_equity=safe_float(info.get("totalStockholderEquity")),
            debt_to_equity=safe_float(info.get("debtToEquity")),
            current_ratio=safe_float(info.get("currentRatio")),
            quick_ratio=safe_float(info.get("quickRatio")),
            beta=safe_float(info.get("beta")),
        )

        # Dividend Metrics
        dividend = DividendMetrics(
            dividend_rate=safe_float(info.get("dividendRate")),
            dividend_yield=safe_float(info.get("dividendYield")),
            payout_ratio=safe_float(info.get("payoutRatio")),
            five_year_avg_dividend_yield=safe_float(
                info.get("fiveYearAvgDividendYield")
            ),
        )

        # Price Metrics
        price = PriceMetrics(
            current_price=safe_float(info.get("currentPrice")),
            previous_close=safe_float(info.get("previousClose")),
            open_price=safe_float(info.get("open")),
            day_high=safe_float(info.get("dayHigh")),
            day_low=safe_float(info.get("dayLow")),
            fifty_two_week_high=safe_float(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=safe_float(info.get("fiftyTwoWeekLow")),
            volume=safe_int(info.get("volume")),
            avg_volume=safe_int(info.get("averageVolume")),
        )

        # Calculate data quality score
        data_quality = self._calculate_data_quality(
            valuation, profitability, cash_flow, leverage, dividend
        )

        # Build complete StockData
        stock_data = StockData(
            company_info=company_info,
            valuation=valuation,
            profitability=profitability,
            cash_flow=cash_flow,
            leverage=leverage,
            dividend=dividend,
            price=price,
            last_updated=datetime.now(),
            data_quality_score=data_quality,
        )

        return stock_data

    def _get_eps_history(self, stock: yf.Ticker) -> Dict[int, float]:
        """
        Get EPS history untuk 5 tahun terakhir.

        Args:
            stock: yfinance Ticker object

        Returns:
            Dictionary dengan {year: eps}
        """
        eps_history = {}

        try:
            # Method 1: Try earnings data first
            earnings = stock.earnings
            if earnings is not None and not earnings.empty:
                logger.debug(
                    f"Earnings data available with columns: {earnings.columns.tolist()}"
                )

                # Try different possible column names
                eps_column = None
                for col in ["Earnings", "EPS", "Earnings Per Share"]:
                    if col in earnings.columns:
                        eps_column = col
                        break

                if eps_column:
                    for year in earnings.index:
                        eps = safe_float(earnings.loc[year, eps_column])
                        if eps is not None:
                            # Convert to year if it's a timestamp
                            year_int = (
                                year.year
                                if hasattr(year, "year")
                                else int(str(year)[:4])
                            )
                            eps_history[year_int] = eps
                    logger.debug(f"EPS history from earnings data: {eps_history}")
                else:
                    logger.debug("No EPS column found in earnings data")

            # Method 2: Calculate EPS from financials if earnings data not available
            if not eps_history:
                financials = stock.financials
                shares = stock.info.get("sharesOutstanding")

                if (
                    financials is not None
                    and not financials.empty
                    and shares is not None
                    and shares > 0
                ):
                    # Try to get Net Income from financials
                    net_income_col = None
                    for col in [
                        "Net Income",
                        "Net Income Applicable To Common Shares",
                        "NetIncome",
                    ]:
                        if col in financials.index:
                            net_income_col = col
                            break

                    if net_income_col:
                        for year in financials.columns:
                            if hasattr(year, "year"):
                                year_int = year.year
                            else:
                                year_int = int(str(year)[:4])

                            net_income = safe_float(
                                financials.loc[net_income_col, year]
                            )
                            if net_income is not None:
                                eps = net_income / shares
                                eps_history[year_int] = eps

                        logger.debug(
                            f"EPS history calculated from financials: {eps_history}"
                        )

            # Method 3: Use trailing EPS as fallback for current year
            if not eps_history:
                trailing_eps = stock.info.get("trailingEps")
                if trailing_eps is not None:
                    current_year = datetime.now().year
                    eps_history[current_year] = trailing_eps
                    logger.debug(f"Using trailing EPS as fallback: {trailing_eps}")

        except Exception as e:
            logger.warning(f"Could not fetch EPS history: {str(e)}")

        return eps_history

    def _calculate_data_quality(
        self,
        valuation: ValuationMetrics,
        profitability: ProfitabilityMetrics,
        cash_flow: CashFlowMetrics,
        leverage: LeverageMetrics,
        dividend: DividendMetrics,
    ) -> float:
        """
        Calculate data quality score berdasarkan kelengkapan data.

        Args:
            Various metrics objects

        Returns:
            Score 0-100 indicating data completeness
        """
        # Critical fields for screening (weight: 1.0 each)
        critical_fields = [
            valuation.pe_ratio,
            valuation.price_to_book,
            valuation.market_cap,
            profitability.roe,
            profitability.gross_margin,
            profitability.eps,
            leverage.debt_to_equity,
            cash_flow.operating_cash_flow,
        ]

        # Additional important fields (weight: 0.5 each)
        additional_fields = [
            valuation.forward_pe,
            profitability.profit_margin,
            profitability.operating_margin,
            cash_flow.free_cash_flow,
            dividend.dividend_yield,
        ]

        # Calculate weighted score
        critical_weight = 1.0
        additional_weight = 0.5

        total_weight = 0
        achieved_weight = 0

        # Process critical fields
        for field in critical_fields:
            total_weight += critical_weight
            if field is not None:
                achieved_weight += critical_weight

        # Process additional fields
        for field in additional_fields:
            total_weight += additional_weight
            if field is not None:
                achieved_weight += additional_weight

        if total_weight == 0:
            return 0.0

        quality_score = (achieved_weight / total_weight) * 100
        return min(quality_score, 100.0)

    def clear_cache(self) -> None:
        """Clear cached stock data."""
        self.cache.clear()
        logger.info("Cache cleared")

    def get_multiple_stocks(
        self, tickers: list[str], use_cache: bool = True, max_workers: int = 5
    ) -> Dict[str, Optional[StockData]]:
        """
        Fetch data untuk multiple stocks concurrently.

        Args:
            tickers: List of ticker symbols
            use_cache: Whether to use cached data
            max_workers: Maximum number of concurrent threads

        Returns:
            Dictionary of {ticker: StockData}
        """
        results = {}

        # If using cache, check what we already have
        uncached_tickers = []
        if use_cache:
            for ticker in tickers:
                normalized_ticker = normalize_ticker(ticker)
                if normalized_ticker in self.cache:
                    results[ticker] = self.cache[normalized_ticker]
                else:
                    uncached_tickers.append(ticker)
        else:
            uncached_tickers = tickers

        # Fetch uncached data concurrently
        if uncached_tickers:
            logger.info(
                f"Fetching {len(uncached_tickers)} stocks concurrently with {max_workers} workers"
            )

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_ticker = {
                    executor.submit(self.get_stock_data, ticker, False): ticker
                    for ticker in uncached_tickers
                }

                # Collect results as they complete
                for future in as_completed(future_to_ticker):
                    ticker = future_to_ticker[future]
                    try:
                        stock_data = future.result()
                        results[ticker] = stock_data
                    except Exception as e:
                        logger.error(f"Failed to fetch data for {ticker}: {str(e)}")
                        results[ticker] = None

        return results
