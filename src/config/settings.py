"""Configuration settings for stock screening criteria and thresholds.

This module contains all the screening criteria thresholds that can be adjusted
based on market conditions or user preferences.
"""

from dataclasses import dataclass, field


@dataclass
class ValuationCriteria:
    """Kriteria valuasi untuk screening emiten."""

    # PE Ratio thresholds
    pe_ratio_preferred: float = 5.0
    pe_ratio_max: float = 15.0

    # PBV thresholds
    pbv_preferred: float = 1.0
    pbv_max: float = 2.0

    # Market Cap (dalam Rupiah)
    market_cap_preferred: float = 100_000_000_000_000  # 100T
    market_cap_min: float = 1_000_000_000_000  # 1T (untuk filter microcap)


@dataclass
class ProfitabilityCriteria:
    """Kriteria profitabilitas dan pertumbuhan."""

    # EPS Growth - harus positif setiap tahun
    eps_growth_years: int = 5
    eps_growth_min_positive: bool = True

    # Gross Profit Margin (dalam %)
    gpm_min: float = 20.0  # Minimal 20%
    gpm_preferred: float = 30.0  # Preferred 30%+

    # Return on Equity (dalam %)
    roe_min: float = 10.0  # Minimal 10%
    roe_preferred: float = 15.0  # Preferred 15%+

    # Operating Cash Flow - harus positif
    ocf_positive: bool = True
    # Free Cash Flow - harus positif
    fcf_positive: bool = True


@dataclass
class RiskCriteria:
    """Kriteria risiko dan leverage."""

    # Debt-to-Equity Ratio
    debt_to_equity_max: float = 1.0  # Maksimal 1.0 (konservatif)
    debt_to_equity_preferred: float = 0.5  # Preferred < 0.5

    # Beta (volatilitas)
    beta_max: float | None = 1.5  # Maksimal 1.5x volatilitas pasar


@dataclass
class DividendCriteria:
    """Kriteria dividen."""

    # Dividend Yield (dalam %)
    dividend_yield_min: float = 2.0  # Minimal 2%
    dividend_yield_preferred: float = 4.0  # Preferred 4%+

    # Apakah wajib ada dividen
    require_dividend: bool = True


@dataclass
class ScreeningCriteria:
    """Gabungan semua kriteria screening."""

    valuation: ValuationCriteria = field(default_factory=ValuationCriteria)
    profitability: ProfitabilityCriteria = field(default_factory=ProfitabilityCriteria)
    risk: RiskCriteria = field(default_factory=RiskCriteria)
    dividend: DividendCriteria = field(default_factory=DividendCriteria)


# Default screening criteria instance
DEFAULT_CRITERIA = ScreeningCriteria()


# Scoring weights untuk ranking
@dataclass
class ScoringWeights:
    """Bobot untuk scoring setiap kriteria."""

    valuation_weight: float = 0.25
    profitability_weight: float = 0.35
    risk_weight: float = 0.20
    dividend_weight: float = 0.20

    def __post_init__(self):
        """Validate that weights sum to 1.0."""
        total = (
            self.valuation_weight
            + self.profitability_weight
            + self.risk_weight
            + self.dividend_weight
        )
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            raise ValueError(f"Weights must sum to 1.0, got {total}")


DEFAULT_WEIGHTS = ScoringWeights()
