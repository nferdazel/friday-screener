"""Data models untuk informasi saham dan data fundamental.

Model ini merepresentasikan data saham yang diambil dari berbagai sumber
(Yahoo Finance, web scraping, dll).
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CompanyInfo:
    """Informasi dasar perusahaan."""

    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None
    description: str | None = None
    website: str | None = None
    country: str | None = None


@dataclass
class ValuationMetrics:
    """Metrik valuasi perusahaan."""

    market_cap: float | None = None
    enterprise_value: float | None = None
    pe_ratio: float | None = None  # Trailing PE
    forward_pe: float | None = None
    peg_ratio: float | None = None
    price_to_book: float | None = None  # PBV
    price_to_sales: float | None = None
    shares_outstanding: float | None = None


@dataclass
class ProfitabilityMetrics:
    """Metrik profitabilitas dan pertumbuhan."""

    # Current metrics
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps: float | None = None  # Earnings Per Share

    # Margins (dalam desimal, e.g., 0.25 = 25%)
    gross_margin: float | None = None  # GPM
    operating_margin: float | None = None
    profit_margin: float | None = None

    # Returns
    roe: float | None = None  # Return on Equity
    roa: float | None = None  # Return on Assets
    roic: float | None = None  # Return on Invested Capital

    # Historical EPS (5 tahun terakhir)
    eps_history: dict[int, float] = field(default_factory=dict)  # {year: eps}


@dataclass
class CashFlowMetrics:
    """Metrik cash flow."""

    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None
    capital_expenditure: float | None = None
    levered_free_cash_flow: float | None = None


@dataclass
class LeverageMetrics:
    """Metrik leverage dan risiko."""

    total_debt: float | None = None
    total_equity: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None
    interest_coverage: float | None = None
    beta: float | None = None  # Volatilitas relatif terhadap market


@dataclass
class DividendMetrics:
    """Metrik dividen."""

    dividend_rate: float | None = None  # Annual dividend per share
    dividend_yield: float | None = None  # Dividend yield (%)
    payout_ratio: float | None = None  # Payout ratio
    five_year_avg_dividend_yield: float | None = None
    dividend_history: list[dict] = field(default_factory=list)  # Historical dividends


@dataclass
class PriceMetrics:
    """Metrik harga saham."""

    current_price: float | None = None
    previous_close: float | None = None
    open_price: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    volume: int | None = None
    avg_volume: int | None = None


@dataclass
class NewsItem:
    """Item berita atau corporate action."""

    title: str
    source: str
    published_date: datetime | None = None
    url: str | None = None
    summary: str | None = None
    sentiment: str | None = None  # positive, negative, neutral


@dataclass
class StockData:
    """Complete stock data model yang menggabungkan semua informasi.

    Model ini adalah representasi lengkap dari sebuah emiten saham
    termasuk data fundamental, teknikal, dan berita.
    """

    # Basic info
    company_info: CompanyInfo

    # Financial metrics
    valuation: ValuationMetrics = field(default_factory=ValuationMetrics)
    profitability: ProfitabilityMetrics = field(default_factory=ProfitabilityMetrics)
    cash_flow: CashFlowMetrics = field(default_factory=CashFlowMetrics)
    leverage: LeverageMetrics = field(default_factory=LeverageMetrics)
    dividend: DividendMetrics = field(default_factory=DividendMetrics)
    price: PriceMetrics = field(default_factory=PriceMetrics)

    # Additional info
    news: list[NewsItem] = field(default_factory=list)
    corporate_actions: list[NewsItem] = field(default_factory=list)

    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    data_quality_score: float | None = None  # 0-100, kualitas data yang tersedia

    def get_ticker(self) -> str:
        """Get stock ticker symbol."""
        return self.company_info.ticker

    def has_complete_data(self) -> bool:
        """Check if stock has complete fundamental data for screening."""
        required_metrics = [
            self.valuation.pe_ratio,
            self.valuation.price_to_book,
            self.profitability.roe,
            self.profitability.gross_margin,
            self.leverage.debt_to_equity,
        ]
        return all(metric is not None for metric in required_metrics)
