"""
Service untuk scraping berita dan corporate action.

Service ini mengambil berita dari berbagai sumber dan melakukan
sentiment analysis sederhana untuk identify positive/negative news.
"""

from datetime import datetime
from typing import List

import time
from typing import List

import yfinance as yf

from src.models.stock_data import NewsItem
from src.utils.helpers import normalize_ticker
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NewsScraperService:
    """Service untuk scraping berita dan corporate action."""

    # Keywords untuk sentiment analysis
    POSITIVE_KEYWORDS = [
        "profit",
        "revenue",
        "growth",
        "increase",
        "gain",
        "positive",
        "expand",
        "acquisition",
        "partnership",
        "dividend",
        "buyback",
        "upgrade",
        "beat",
        "exceed",
        "strong",
        "laba",
        "naik",
        "tumbuh",
        "positif",
        "dividen",
    ]

    NEGATIVE_KEYWORDS = [
        "loss",
        "decline",
        "decrease",
        "fall",
        "drop",
        "negative",
        "weak",
        "downgrade",
        "miss",
        "below",
        "concern",
        "risk",
        "fraud",
        "lawsuit",
        "investigation",
        "rugi",
        "turun",
        "merosot",
        "negatif",
        "penurunan",
    ]

    CORPORATE_ACTION_KEYWORDS = [
        "stock split",
        "reverse split",
        "dividend",
        "rights issue",
        "buyback",
        "merger",
        "acquisition",
        "ipo",
        "delisting",
        "bonus share",
        "stock dividend",
        "pemecahan saham",
        "right issue",
        "akuisisi",
        "penggabungan",
    ]

    def __init__(self, max_news: int = 10):
        """
        Initialize news scraper service.

        Args:
            max_news: Maximum number of news items to fetch
        """
        self.max_news = max_news

    def get_news(self, ticker: str) -> List[NewsItem]:
        """
        Get news untuk ticker tertentu.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of NewsItem
        """
        normalized_ticker = normalize_ticker(ticker)
        logger.info(f"Fetching news for {normalized_ticker}...")

        news_items = []

        # Get news from Yahoo Finance
        yahoo_news = self._get_yahoo_finance_news(normalized_ticker)
        news_items.extend(yahoo_news)

        # Could add more sources here:
        # - idx_news = self._get_idx_news(ticker)
        # - investing_news = self._get_investing_com_news(ticker)

        # Sort by date (most recent first)
        news_items.sort(key=lambda x: x.published_date or datetime.min, reverse=True)

        # Limit to max_news
        news_items = news_items[: self.max_news]

        logger.info(f"Found {len(news_items)} news items for {normalized_ticker}")
        return news_items

    def _get_yahoo_finance_news(self, ticker: str) -> List[NewsItem]:
        """
        Get news dari Yahoo Finance.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of NewsItem
        """
        news_items = []
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                stock = yf.Ticker(ticker)
                news_data = stock.news

                if not news_data:
                    logger.debug(f"No news found for {ticker}")
                    return news_items

                for item in news_data[: self.max_news]:
                    # Parse timestamp
                    published_date = None
                    if 'providerPublishTime' in item:
                        try:
                            published_date = datetime.fromtimestamp(
                                item['providerPublishTime']
                            )
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Invalid timestamp for news item: {e}")

                    # Create NewsItem with validation
                    title = item.get('title', '').strip()
                    if not title:
                        continue  # Skip items with no title
                        
                    news_item = NewsItem(
                        title=title,
                        source=item.get('publisher', 'Yahoo Finance'),
                        published_date=published_date,
                        url=item.get('link'),
                        summary=item.get('summary', '').strip()[:500],  # Limit summary length
                        sentiment=self._analyze_sentiment(
                            title + ' ' + (item.get('summary', '') or '')
                        ),
                    )

                    news_items.append(news_item)

                logger.info(f"Successfully fetched {len(news_items)} news items for {ticker}")
                break  # Success, exit retry loop

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {ticker}: {str(e)}")
                
                if attempt < max_retries - 1:
                    logger.debug(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch news for {ticker} after {max_retries} attempts")
                    # Return empty list instead of raising exception
                    return []

        return news_items

            for item in news_data[: self.max_news]:
                # Parse timestamp
                published_date = None
                if "providerPublishTime" in item:
                    published_date = datetime.fromtimestamp(item["providerPublishTime"])

                # Create NewsItem
                news_item = NewsItem(
                    title=item.get("title", ""),
                    source=item.get("publisher", "Yahoo Finance"),
                    published_date=published_date,
                    url=item.get("link"),
                    summary=item.get("summary"),
                    sentiment=self._analyze_sentiment(
                        item.get("title", "") + " " + item.get("summary", "")
                    ),
                )

                news_items.append(news_item)

        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance news: {str(e)}")

        return news_items

    def get_corporate_actions(self, ticker: str) -> List[NewsItem]:
        """
        Get corporate actions dari news.

        Filter news yang mengandung corporate action keywords.

        Args:
            ticker: Stock ticker symbol

        Returns:
            List of NewsItem yang merupakan corporate actions
        """
        all_news = self.get_news(ticker)

        corporate_actions = []
        for news in all_news:
            if self._is_corporate_action(news):
                corporate_actions.append(news)

        logger.info(
            f"Found {len(corporate_actions)} corporate action items for {ticker}"
        )
        return corporate_actions

    def _is_corporate_action(self, news: NewsItem) -> bool:
        """
        Check apakah news item adalah corporate action.

        Args:
            news: NewsItem to check

        Returns:
            True if news is about corporate action
        """
        text = (news.title + " " + (news.summary or "")).lower()

        for keyword in self.CORPORATE_ACTION_KEYWORDS:
            if keyword.lower() in text:
                return True

        return False

    def _analyze_sentiment(self, text: str) -> str:
        """
        Analyze sentiment dari text (simple keyword-based).

        Args:
            text: Text to analyze

        Returns:
            'positive', 'negative', or 'neutral'
        """
        if not text:
            return "neutral"

        text_lower = text.lower()

        positive_count = sum(
            1 for keyword in self.POSITIVE_KEYWORDS if keyword in text_lower
        )
        negative_count = sum(
            1 for keyword in self.NEGATIVE_KEYWORDS if keyword in text_lower
        )

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _get_idx_news(self, ticker: str) -> List[NewsItem]:
        """
        Get news dari idx.co.id (Indonesia Stock Exchange).

        Note: This is a placeholder for future implementation.
        IDX website structure might require specific scraping logic.

        Args:
            ticker: Stock ticker (without .JK suffix)

        Returns:
            List of NewsItem
        """
        news_items = []

        try:
            # This would require specific implementation based on IDX website structure
            # Example structure (not actual implementation):
            # ticker_clean = ticker.replace('.JK', '')
            # url = f"https://www.idx.co.id/perusahaan-tercatat/profil-perusahaan-tercatat/?kodeEmiten={ticker_clean}"
            # response = requests.get(url, timeout=10)
            # Parse HTML and extract news

            logger.info("IDX news scraping not yet implemented - placeholder only")

        except Exception as e:
            logger.error(f"Error fetching IDX news: {str(e)}")

        return news_items

    def _get_investing_com_news(self, ticker: str) -> List[NewsItem]:
        """
        Get news dari Investing.com.

        Note: This is a placeholder for future implementation.
        Investing.com might have anti-scraping measures.

        Args:
            ticker: Stock ticker

        Returns:
            List of NewsItem
        """
        news_items = []

        try:
            # This would require:
            # 1. Mapping ticker to Investing.com stock ID
            # 2. Proper headers to avoid anti-scraping
            # 3. Parsing their HTML structure

            logger.info(
                "Investing.com news scraping not yet implemented - placeholder only"
            )

        except Exception as e:
            logger.error(f"Error fetching Investing.com news: {str(e)}")

        return news_items

    def analyze_news_impact(self, news_items: List[NewsItem]) -> dict:
        """
        Analyze overall impact dari news items.

        Args:
            news_items: List of news items

        Returns:
            Dictionary dengan analisis:
            - positive_count
            - negative_count
            - neutral_count
            - overall_sentiment
            - key_events: List of important events
        """
        positive = sum(1 for n in news_items if n.sentiment == "positive")
        negative = sum(1 for n in news_items if n.sentiment == "negative")
        neutral = sum(1 for n in news_items if n.sentiment == "neutral")

        # Determine overall sentiment
        if positive > negative * 1.5:
            overall = "positive"
        elif negative > positive * 1.5:
            overall = "negative"
        else:
            overall = "neutral"

        # Identify key events (negative news or corporate actions)
        key_events = [
            n.title
            for n in news_items
            if n.sentiment == "negative" or self._is_corporate_action(n)
        ]

        return {
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "overall_sentiment": overall,
            "key_events": key_events[:5],  # Top 5 key events
            "total_news": len(news_items),
        }
