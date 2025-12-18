"""
Wrestling news aggregator scraper.

Scrapes from multiple wrestling news sources to keep WrestleBot informed
about current events, breaking news, and industry developments.

Sources:
- PWInsider (pwinsider.com)
- Wrestling Inc (wrestlinginc.com)
- WrestleZone (wrestlezone.com)
- Wrestling Observer/F4W Online (f4wonline.com)

We only scrape factual news headlines, dates, and basic summaries.
We do NOT scrape full articles, commentary, or opinion pieces.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper, retry_on_failure

logger = logging.getLogger(__name__)


class WrestlingNewsScraper(BaseScraper):
    """
    Scraper for wrestling news from multiple sources.
    Aggregates headlines and basic info to keep AI knowledgeable about current events.
    """

    SOURCE_NAME = "wrestling_news"
    BASE_URL = "https://www.wrestlinginc.com"  # Primary source

    # Conservative limits - news sites can be heavy
    REQUESTS_PER_MINUTE = 10
    REQUESTS_PER_HOUR = 100
    REQUESTS_PER_DAY = 1000

    NEWS_SOURCES = {
        "wrestlinginc": {
            "url": "https://www.wrestlinginc.com/news/",
            "enabled": True,
        },
        "wrestlezone": {
            "url": "https://www.wrestlezone.com/news/",
            "enabled": True,
        },
        # PWInsider and F4W require subscriptions for most content
        # Skip for now to avoid paywall issues
    }

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        text = " ".join(text.split())
        return text.strip()

    def _parse_date(self, text: str) -> Optional[str]:
        """Parse various date formats from news sites."""
        if not text:
            return None

        # Handle relative dates like "2 hours ago", "1 day ago"
        relative_match = re.search(r"(\d+)\s+(hour|day|minute)s?\s+ago", text.lower())
        if relative_match:
            amount = int(relative_match.group(1))
            unit = relative_match.group(2)
            now = datetime.now()
            if unit == "minute":
                dt = now - timedelta(minutes=amount)
            elif unit == "hour":
                dt = now - timedelta(hours=amount)
            elif unit == "day":
                dt = now - timedelta(days=amount)
            else:
                dt = now
            return dt.strftime("%Y-%m-%d")

        # Standard date patterns
        patterns = [
            (r"(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),
            (r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", "%B %d, %Y"),
            (r"(\d{1,2})/(\d{1,2})/(\d{4})", "%m/%d/%Y"),
        ]

        for pattern, date_format in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if "-" in date_format:
                        date_str = f"{groups[0]}-{groups[1]}-{groups[2]}"
                    elif "/" in date_format:
                        date_str = f"{groups[0]}/{groups[1]}/{groups[2]}"
                    else:
                        date_str = f"{groups[0]} {groups[1]}, {groups[2]}"
                    dt = datetime.strptime(date_str, date_format)
                    return dt.strftime("%Y-%m-%d")
                except (ValueError, IndexError):
                    continue

        return None

    @retry_on_failure(max_retries=2)
    def scrape_wrestling_inc_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Scrape recent headlines from Wrestling Inc."""
        url = self.NEWS_SOURCES["wrestlinginc"]["url"]
        response = self.fetch(url)

        if not response:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        news_items = []

        # Wrestling Inc uses article cards
        articles = soup.find_all("article", limit=limit * 2)  # Get extra in case some fail

        for article in articles:
            if len(news_items) >= limit:
                break

            try:
                # Extract headline
                headline_tag = article.find("h2") or article.find("h3") or article.find("a", class_=re.compile("title|headline"))
                if not headline_tag:
                    continue

                headline = self._clean_text(headline_tag.get_text())
                if not headline:
                    continue

                # Extract URL
                link_tag = headline_tag.find("a") if headline_tag.name != "a" else headline_tag
                article_url = link_tag.get("href") if link_tag else None
                if article_url and not article_url.startswith("http"):
                    article_url = urljoin(url, article_url)

                # Extract date
                date_tag = article.find("time") or article.find(class_=re.compile("date|time|published"))
                published_date = None
                if date_tag:
                    date_text = date_tag.get("datetime") or date_tag.get_text()
                    published_date = self._parse_date(date_text)

                # Extract category/tags if available
                category = None
                category_tag = article.find(class_=re.compile("category|tag"))
                if category_tag:
                    category = self._clean_text(category_tag.get_text())

                news_item = {
                    "source": "wrestlinginc",
                    "headline": headline,
                    "url": article_url,
                    "published_date": published_date or datetime.now().strftime("%Y-%m-%d"),
                    "category": category,
                }

                news_items.append(news_item)
                logger.debug(f"Scraped news: {headline}")

            except Exception as e:
                logger.warning(f"Failed to parse news article: {e}")
                continue

        logger.info(f"Scraped {len(news_items)} news items from Wrestling Inc")
        return news_items

    @retry_on_failure(max_retries=2)
    def scrape_wrestlezone_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Scrape recent headlines from WrestleZone."""
        url = self.NEWS_SOURCES["wrestlezone"]["url"]
        response = self.fetch(url)

        if not response:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        news_items = []

        # WrestleZone structure
        articles = soup.find_all(["article", "div"], class_=re.compile("post|article|news-item"), limit=limit * 2)

        for article in articles:
            if len(news_items) >= limit:
                break

            try:
                # Extract headline
                headline_tag = article.find(["h1", "h2", "h3"], class_=re.compile("title|headline|entry-title"))
                if not headline_tag:
                    headline_tag = article.find("a", class_=re.compile("title|headline"))

                if not headline_tag:
                    continue

                headline = self._clean_text(headline_tag.get_text())
                if not headline or len(headline) < 10:  # Skip if too short
                    continue

                # Extract URL
                link_tag = headline_tag.find("a") if headline_tag.name != "a" else headline_tag
                article_url = link_tag.get("href") if link_tag else None
                if article_url and not article_url.startswith("http"):
                    article_url = urljoin(url, article_url)

                # Extract date
                date_tag = article.find("time") or article.find(class_=re.compile("date|time|published|meta"))
                published_date = None
                if date_tag:
                    date_text = date_tag.get("datetime") or date_tag.get_text()
                    published_date = self._parse_date(date_text)

                news_item = {
                    "source": "wrestlezone",
                    "headline": headline,
                    "url": article_url,
                    "published_date": published_date or datetime.now().strftime("%Y-%m-%d"),
                    "category": None,
                }

                news_items.append(news_item)
                logger.debug(f"Scraped news: {headline}")

            except Exception as e:
                logger.warning(f"Failed to parse WrestleZone article: {e}")
                continue

        logger.info(f"Scraped {len(news_items)} news items from WrestleZone")
        return news_items

    def scrape_all_news(self, per_source_limit: int = 10) -> List[Dict[str, Any]]:
        """
        Scrape news from all enabled sources.

        Args:
            per_source_limit: Max headlines to get from each source

        Returns:
            Combined list of news items from all sources
        """
        all_news = []

        # Scrape each enabled source
        for source_name, config in self.NEWS_SOURCES.items():
            if not config.get("enabled", True):
                continue

            try:
                if source_name == "wrestlinginc":
                    items = self.scrape_wrestling_inc_news(limit=per_source_limit)
                elif source_name == "wrestlezone":
                    items = self.scrape_wrestlezone_news(limit=per_source_limit)
                else:
                    continue

                all_news.extend(items)

            except Exception as e:
                logger.error(f"Failed to scrape {source_name}: {e}")
                continue

        logger.info(f"Scraped total of {len(all_news)} news items from all sources")
        return all_news
