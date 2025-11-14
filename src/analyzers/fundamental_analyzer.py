"""
Fundamental Analyzer untuk screening saham berdasarkan kriteria fundamental.

Analyzer ini melakukan analisis komprehensif terhadap data fundamental saham
dan menghasilkan scoring serta rekomendasi berdasarkan kriteria yang ditentukan.
"""

from typing import List

from src.config.settings import (
    DEFAULT_CRITERIA,
    DEFAULT_WEIGHTS,
    ScoringWeights,
    ScreeningCriteria,
)
from src.models.screening_result import (
    CategoryScore,
    ScreeningMetrics,
    ScreeningResult,
)
from src.models.stock_data import StockData
from src.utils.helpers import is_growing_trend
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FundamentalAnalyzer:
    """Analyzer untuk fundamental screening."""

    def __init__(
        self,
        criteria: ScreeningCriteria = DEFAULT_CRITERIA,
        weights: ScoringWeights = DEFAULT_WEIGHTS,
    ):
        """
        Initialize fundamental analyzer.

        Args:
            criteria: Screening criteria thresholds
            weights: Scoring weights untuk setiap kategori
        """
        self.criteria = criteria
        self.weights = weights

    def analyze(self, stock_data: StockData) -> ScreeningResult:
        """
        Perform complete fundamental analysis.

        Args:
            stock_data: StockData object dengan data fundamental

        Returns:
            ScreeningResult dengan scoring dan insights
        """
        logger.info(f"Analyzing {stock_data.get_ticker()}...")

        # Initialize result
        result = ScreeningResult(
            ticker=stock_data.get_ticker(),
            company_name=stock_data.company_info.name,
            sector=stock_data.company_info.sector,
            industry=stock_data.company_info.industry,
            data_completeness=stock_data.data_quality_score or 0.0,
        )

        # Check data completeness
        if not stock_data.has_complete_data():
            logger.warning(
                f"Incomplete data for {stock_data.get_ticker()}, "
                f"quality score: {stock_data.data_quality_score}"
            )
            result.add_red_flag(
                "Data tidak lengkap - beberapa metrik fundamental tidak tersedia"
            )

        # Analyze each category
        result.metrics.valuation_score = self._analyze_valuation(stock_data, result)
        result.metrics.profitability_score = self._analyze_profitability(
            stock_data, result
        )
        result.metrics.risk_score = self._analyze_risk(stock_data, result)
        result.metrics.dividend_score = self._analyze_dividend(stock_data, result)

        # Calculate total score
        result.metrics.total_score = self._calculate_total_score(result.metrics)

        # Generate rating
        result.rating = result.calculate_rating_from_score()

        # Add key metrics summary
        result.key_metrics = self._build_key_metrics_summary(stock_data)

        logger.info(
            f"Analysis complete for {stock_data.get_ticker()}: "
            f"Score={result.metrics.total_score:.1f}, Rating={result.rating.value}"
        )

        return result

    def _analyze_valuation(
        self, stock_data: StockData, result: ScreeningResult
    ) -> CategoryScore:
        """
        Analyze valuation metrics.

        Kriteria:
        - PE Ratio: Prefer ≤ 5, max < 15
        - PBV: Prefer ≤ 1, max < 2
        - Market Cap: Prefer besar (≥ 100T)
        """
        score = CategoryScore(
            category="Valuation", score=0.0, weight=self.weights.valuation_weight
        )
        details = {}

        pe = stock_data.valuation.pe_ratio
        pbv = stock_data.valuation.price_to_book
        market_cap = stock_data.valuation.market_cap

        # PE Ratio scoring (40 points)
        if pe is not None and pe > 0:
            if pe <= self.criteria.valuation.pe_ratio_preferred:
                score.score += 40
                result.add_strength(f"PE Ratio sangat baik: {pe:.2f}")
            elif pe <= self.criteria.valuation.pe_ratio_max:
                score.score += 25
                result.add_insight(
                    "Valuation",
                    "positive",
                    "PE Ratio acceptable",
                    f"PE Ratio {pe:.2f} masih dalam range acceptable (< {self.criteria.valuation.pe_ratio_max})",
                    "Medium",
                )
            else:
                score.score += 10
                result.add_weakness(
                    f"PE Ratio tinggi: {pe:.2f} (> {self.criteria.valuation.pe_ratio_max})"
                )
            details["pe_ratio"] = pe
        else:
            result.add_weakness("PE Ratio tidak tersedia")

        # PBV scoring (40 points)
        if pbv is not None and pbv > 0:
            if pbv <= self.criteria.valuation.pbv_preferred:
                score.score += 40
                result.add_strength(f"PBV sangat baik: {pbv:.2f} (undervalued)")
            elif pbv <= self.criteria.valuation.pbv_max:
                score.score += 25
                result.add_insight(
                    "Valuation",
                    "positive",
                    "PBV acceptable",
                    f"PBV {pbv:.2f} masih reasonable (< {self.criteria.valuation.pbv_max})",
                    "Medium",
                )
            else:
                score.score += 10
                result.add_weakness(
                    f"PBV tinggi: {pbv:.2f} (> {self.criteria.valuation.pbv_max})"
                )
            details["pbv"] = pbv
        else:
            result.add_weakness("PBV tidak tersedia")

        # Market Cap scoring (20 points)
        if market_cap is not None:
            if market_cap >= self.criteria.valuation.market_cap_preferred:
                score.score += 20
                result.add_strength("Market cap besar - blue chip stock")
            elif market_cap >= self.criteria.valuation.market_cap_min:
                score.score += 15
                result.add_insight(
                    "Valuation",
                    "neutral",
                    "Market cap moderate",
                    "Market capitalization dalam range moderate",
                    "Low",
                )
            else:
                score.score += 5
                result.add_red_flag("Market cap kecil - risiko likuiditas tinggi")
            details["market_cap"] = market_cap
        else:
            result.add_weakness("Market cap tidak tersedia")

        score.details = details
        score.passed = score.score >= 50  # Pass jika score >= 50%

        return score

    def _analyze_profitability(
        self, stock_data: StockData, result: ScreeningResult
    ) -> CategoryScore:
        """
        Analyze profitability and growth metrics.

        Kriteria:
        - EPS growth: Harus positif 5 tahun terakhir
        - Gross Margin: Prefer ≥ 30%, min 20%
        - ROE: Prefer ≥ 15%, min 10%
        - Cash Flow: Harus positif
        """
        score = CategoryScore(
            category="Profitability",
            score=0.0,
            weight=self.weights.profitability_weight,
        )
        details = {}

        # EPS growth analysis (30 points)
        eps_history = stock_data.profitability.eps_history
        if len(eps_history) >= 2:
            years = sorted(eps_history.keys())
            eps_values = [eps_history[year] for year in years]

            # Check if growing
            if is_growing_trend(eps_values, min_positive_years=3):
                score.score += 30
                result.add_strength(
                    f"EPS tumbuh konsisten dalam {len(eps_values)} tahun terakhir"
                )
            else:
                # Check for recent growth (last 2 years)
                if len(eps_values) >= 2 and eps_values[-1] > eps_values[-2]:
                    score.score += 15
                    result.add_insight(
                        "Profitability",
                        "neutral",
                        "EPS recovery",
                        "EPS menunjukkan recovery di tahun terakhir",
                        "Medium",
                    )
                else:
                    score.score += 5
                    result.add_red_flag("EPS tidak menunjukkan pertumbuhan konsisten")
            details["eps_trend"] = (
                "growing" if is_growing_trend(eps_values) else "declining"
            )
            details["eps_history"] = eps_history
        else:
            result.add_weakness("Historical EPS data tidak cukup")

        # Gross Margin analysis (25 points)
        gpm = stock_data.profitability.gross_margin
        if gpm is not None:
            gpm_pct = gpm * 100 if gpm <= 1 else gpm
            if gpm_pct >= self.criteria.profitability.gpm_preferred:
                score.score += 25
                result.add_strength(f"Gross margin excellent: {gpm_pct:.1f}%")
            elif gpm_pct >= self.criteria.profitability.gpm_min:
                score.score += 15
                result.add_insight(
                    "Profitability",
                    "positive",
                    "Gross margin acceptable",
                    f"Gross margin {gpm_pct:.1f}% dalam range sehat",
                    "Medium",
                )
            else:
                score.score += 5
                result.add_weakness(
                    f"Gross margin rendah: {gpm_pct:.1f}% (< {self.criteria.profitability.gpm_min}%)"
                )
            details["gross_margin"] = gpm_pct
        else:
            result.add_weakness("Gross margin tidak tersedia")

        # ROE analysis (25 points)
        roe = stock_data.profitability.roe
        if roe is not None:
            roe_pct = roe * 100 if roe <= 1 else roe
            if roe_pct >= self.criteria.profitability.roe_preferred:
                score.score += 25
                result.add_strength(f"ROE excellent: {roe_pct:.1f}%")
            elif roe_pct >= self.criteria.profitability.roe_min:
                score.score += 15
                result.add_insight(
                    "Profitability",
                    "positive",
                    "ROE acceptable",
                    f"ROE {roe_pct:.1f}% menunjukkan profitabilitas yang baik",
                    "Medium",
                )
            else:
                score.score += 5
                result.add_weakness(
                    f"ROE rendah: {roe_pct:.1f}% (< {self.criteria.profitability.roe_min}%)"
                )
            details["roe"] = roe_pct
        else:
            result.add_weakness("ROE tidak tersedia")

        # Cash Flow analysis (20 points)
        ocf = stock_data.cash_flow.operating_cash_flow
        fcf = stock_data.cash_flow.free_cash_flow

        if ocf is not None and ocf > 0:
            score.score += 10
            result.add_strength("Operating cash flow positif")
            details["ocf_positive"] = True
        elif ocf is not None:
            result.add_red_flag("Operating cash flow negatif - masalah arus kas")
            details["ocf_positive"] = False
        else:
            result.add_weakness("Operating cash flow tidak tersedia")

        if fcf is not None and fcf > 0:
            score.score += 10
            result.add_strength("Free cash flow positif")
            details["fcf_positive"] = True
        elif fcf is not None:
            result.add_weakness("Free cash flow negatif")
            details["fcf_positive"] = False
        else:
            result.add_weakness("Free cash flow tidak tersedia")

        score.details = details
        score.passed = score.score >= 50

        return score

    def _analyze_risk(
        self, stock_data: StockData, result: ScreeningResult
    ) -> CategoryScore:
        """
        Analyze risk and leverage metrics.

        Kriteria:
        - Debt-to-Equity: Prefer < 0.5, max < 1.0
        - Beta: Max 1.5
        """
        score = CategoryScore(
            category="Risk", score=0.0, weight=self.weights.risk_weight
        )
        details = {}

        # Debt-to-Equity analysis (70 points)
        dte = stock_data.leverage.debt_to_equity
        if dte is not None:
            if dte <= self.criteria.risk.debt_to_equity_preferred:
                score.score += 70
                result.add_strength(
                    f"Debt-to-Equity sangat rendah: {dte:.2f} - leverage konservatif"
                )
            elif dte <= self.criteria.risk.debt_to_equity_max:
                score.score += 45
                result.add_insight(
                    "Risk",
                    "neutral",
                    "Debt level acceptable",
                    f"Debt-to-Equity {dte:.2f} masih dalam range aman",
                    "Medium",
                )
            else:
                score.score += 15
                result.add_red_flag(
                    f"Debt-to-Equity tinggi: {dte:.2f} - risiko leverage tinggi"
                )
            details["debt_to_equity"] = dte
        else:
            result.add_weakness("Debt-to-Equity tidak tersedia")

        # Beta analysis (30 points)
        beta = stock_data.leverage.beta
        if beta is not None:
            if beta <= 1.0:
                score.score += 30
                result.add_strength(
                    f"Beta rendah: {beta:.2f} - volatilitas lebih rendah dari market"
                )
            elif (
                self.criteria.risk.beta_max is not None
                and beta <= self.criteria.risk.beta_max
            ):
                score.score += 20
                result.add_insight(
                    "Risk",
                    "neutral",
                    "Beta moderate",
                    f"Beta {beta:.2f} - volatilitas moderate",
                    "Low",
                )
            else:
                score.score += 5
                result.add_weakness(
                    f"Beta tinggi: {beta:.2f} - volatilitas lebih tinggi dari market"
                )
            details["beta"] = beta
        else:
            # Jika beta tidak ada, berikan score moderate
            score.score += 15
            result.add_insight(
                "Risk",
                "neutral",
                "Beta data unavailable",
                "Data volatilitas (beta) tidak tersedia",
                "Low",
            )

        score.details = details
        score.passed = score.score >= 50

        return score

    def _analyze_dividend(
        self, stock_data: StockData, result: ScreeningResult
    ) -> CategoryScore:
        """
        Analyze dividend metrics.

        Kriteria:
        - Dividend: Harus ada
        - Dividend Yield: Prefer ≥ 4%, min 2%
        """
        score = CategoryScore(
            category="Dividend", score=0.0, weight=self.weights.dividend_weight
        )
        details = {}

        div_yield = stock_data.dividend.dividend_yield

        if div_yield is not None and div_yield > 0:
            div_yield_pct = div_yield * 100 if div_yield <= 1 else div_yield

            if div_yield_pct >= self.criteria.dividend.dividend_yield_preferred:
                score.score += 100
                result.add_strength(f"Dividend yield sangat baik: {div_yield_pct:.2f}%")
            elif div_yield_pct >= self.criteria.dividend.dividend_yield_min:
                score.score += 60
                result.add_insight(
                    "Dividend",
                    "positive",
                    "Dividend yield acceptable",
                    f"Dividend yield {div_yield_pct:.2f}% memberikan return yang reasonable",
                    "Medium",
                )
            else:
                score.score += 30
                result.add_weakness(
                    f"Dividend yield rendah: {div_yield_pct:.2f}% (< {self.criteria.dividend.dividend_yield_min}%)"
                )

            details["dividend_yield"] = div_yield_pct
            details["has_dividend"] = True

        else:
            # No dividend
            if self.criteria.dividend.require_dividend:
                score.score += 0
                result.add_red_flag("Tidak membayar dividen")
            else:
                score.score += 20
                result.add_weakness("Tidak membayar dividen")

            details["has_dividend"] = False

        score.details = details
        score.passed = score.score >= 40  # More lenient for dividend

        return score

    def _calculate_total_score(self, metrics: ScreeningMetrics) -> float:
        """
        Calculate weighted total score.

        Args:
            metrics: ScreeningMetrics dengan category scores

        Returns:
            Weighted total score (0-100)
        """
        total = (
            metrics.valuation_score.score * self.weights.valuation_weight
            + metrics.profitability_score.score * self.weights.profitability_weight
            + metrics.risk_score.score * self.weights.risk_weight
            + metrics.dividend_score.score * self.weights.dividend_weight
        )

        return round(total, 2)

    def _build_key_metrics_summary(self, stock_data: StockData) -> dict:
        """
        Build summary of key metrics untuk quick view.

        Args:
            stock_data: StockData object

        Returns:
            Dictionary of key metrics
        """
        return {
            "pe_ratio": stock_data.valuation.pe_ratio,
            "pbv": stock_data.valuation.price_to_book,
            "market_cap": stock_data.valuation.market_cap,
            "roe": stock_data.profitability.roe,
            "gross_margin": stock_data.profitability.gross_margin,
            "debt_to_equity": stock_data.leverage.debt_to_equity,
            "dividend_yield": stock_data.dividend.dividend_yield,
            "current_price": stock_data.price.current_price,
            "eps": stock_data.profitability.eps,
        }

    def batch_analyze(self, stocks_data: List[StockData]) -> List[ScreeningResult]:
        """
        Analyze multiple stocks.

        Args:
            stocks_data: List of StockData objects

        Returns:
            List of ScreeningResult, sorted by score (descending)
        """
        results = []

        for stock_data in stocks_data:
            result = self.analyze(stock_data)
            results.append(result)

        # Sort by total score
        results.sort(key=lambda x: x.metrics.total_score, reverse=True)

        return results
