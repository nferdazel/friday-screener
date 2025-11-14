"""
Model untuk hasil screening saham.

Model ini merepresentasikan hasil analisis dan screening dari sebuah emiten,
termasuk score, rating, dan insights.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Rating(Enum):
    """Rating kategori untuk hasil screening (neutral, bukan rekomendasi)."""

    VERY_STRONG = "VERY_STRONG"
    STRONG = "STRONG"
    FAIR = "FAIR"
    WEAK = "WEAK"
    VERY_WEAK = "VERY_WEAK"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

    def __str__(self) -> str:
        """String representation untuk display."""
        mapping = {
            Rating.VERY_STRONG: "Very Strong ⭐⭐⭐",
            Rating.STRONG: "Strong ⭐⭐",
            Rating.FAIR: "Fair ⭐",
            Rating.WEAK: "Weak ⚠️",
            Rating.VERY_WEAK: "Very Weak ⚠️⚠️",
            Rating.INSUFFICIENT_DATA: "Insufficient Data ❓",
        }
        return mapping.get(self, self.value)


@dataclass
class CategoryScore:
    """Score untuk satu kategori screening."""

    category: str
    score: float  # 0-100
    max_score: float = 100.0
    weight: float = 0.0
    passed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreeningMetrics:
    """Metrik-metrik hasil screening."""

    # Overall
    total_score: float = 0.0  # 0-100
    max_possible_score: float = 100.0

    # Category scores
    valuation_score: CategoryScore = field(
        default_factory=lambda: CategoryScore("Valuation", 0.0)
    )
    profitability_score: CategoryScore = field(
        default_factory=lambda: CategoryScore("Profitability", 0.0)
    )
    risk_score: CategoryScore = field(
        default_factory=lambda: CategoryScore("Risk", 0.0)
    )
    dividend_score: CategoryScore = field(
        default_factory=lambda: CategoryScore("Dividend", 0.0)
    )

    def get_all_category_scores(self) -> List[CategoryScore]:
        """Get all category scores as list."""
        return [
            self.valuation_score,
            self.profitability_score,
            self.risk_score,
            self.dividend_score,
        ]


@dataclass
class Insight:
    """Single insight atau finding dari analisis."""

    category: str  # Valuation, Profitability, Risk, Dividend, News
    severity: str  # positive, negative, neutral, warning
    title: str
    description: str
    impact: Optional[str] = None  # High, Medium, Low


@dataclass
class ScreeningResult:
    """
    Complete result dari stock screening.

    Model ini berisi semua hasil analisis, scoring, dan insights
    untuk sebuah emiten saham.
    """

    ticker: str
    company_name: str
    sector: Optional[str] = None
    industry: Optional[str] = None

    # Screening results
    rating: Rating = Rating.INSUFFICIENT_DATA
    metrics: ScreeningMetrics = field(default_factory=ScreeningMetrics)

    # Insights and findings
    insights: List[Insight] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    # Key metrics summary (untuk quick view)
    key_metrics: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    screened_at: datetime = field(default_factory=datetime.now)
    data_completeness: float = 0.0  # 0-100%

    def add_insight(
        self,
        category: str,
        severity: str,
        title: str,
        description: str,
        impact: Optional[str] = None,
    ) -> None:
        """Add new insight to the result."""
        insight = Insight(
            category=category,
            severity=severity,
            title=title,
            description=description,
            impact=impact,
        )
        self.insights.append(insight)

    def add_red_flag(self, message: str) -> None:
        """Add red flag (warning/negative finding)."""
        self.red_flags.append(message)

    def add_strength(self, message: str) -> None:
        """Add strength (positive finding)."""
        self.strengths.append(message)

    def add_weakness(self, message: str) -> None:
        """Add weakness (area of concern)."""
        self.weaknesses.append(message)

    def get_insights_by_category(self, category: str) -> List[Insight]:
        """Get all insights for a specific category."""
        return [i for i in self.insights if i.category == category]

    def get_insights_by_severity(self, severity: str) -> List[Insight]:
        """Get all insights with specific severity."""
        return [i for i in self.insights if i.severity == severity]

    def is_strong_fundamentals(self) -> bool:
        """Check if this stock has strong fundamentals."""
        return self.rating in [Rating.STRONG, Rating.VERY_STRONG]

    def calculate_rating_from_score(self) -> Rating:
        """
        Calculate rating based on total score.

        Score ranges:
        - 80-100: Very Strong (fundamentals sangat kuat)
        - 60-79: Strong (fundamentals kuat)
        - 40-59: Fair (fundamentals cukup)
        - 20-39: Weak (fundamentals lemah)
        - 0-19: Very Weak (fundamentals sangat lemah)
        """
        score = self.metrics.total_score

        if score >= 80:
            return Rating.VERY_STRONG
        elif score >= 60:
            return Rating.STRONG
        elif score >= 40:
            return Rating.FAIR
        elif score >= 20:
            return Rating.WEAK
        else:
            return Rating.VERY_WEAK

    def summary(self) -> str:
        """Get summary of screening result."""
        return f"""
Screening Result for {self.ticker} - {self.company_name}
Rating: {self.rating}
Total Score: {self.metrics.total_score:.1f}/100
Data Completeness: {self.data_completeness:.1f}%

Category Scores:
- Valuation: {self.metrics.valuation_score.score:.1f}/100
- Profitability: {self.metrics.profitability_score.score:.1f}/100
- Risk: {self.metrics.risk_score.score:.1f}/100
- Dividend: {self.metrics.dividend_score.score:.1f}/100

Strengths: {len(self.strengths)}
Weaknesses: {len(self.weaknesses)}
Red Flags: {len(self.red_flags)}
        """.strip()
