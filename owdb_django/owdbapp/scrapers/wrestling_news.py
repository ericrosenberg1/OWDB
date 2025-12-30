"""
Wrestling news aggregator scraper.

Scrapes from multiple wrestling news sources to keep the database informed
about current events, breaking news, and industry developments.

Sources:
- Wrestling Inc (wrestlinginc.com) - Full articles + RSS
- WrestleZone (wrestlezone.com) - Full articles + RSS
- PWTorch (pwtorch.com) - Free tier articles + RSS
- Ringside News (ringsidenews.com) - Full articles + RSS
- Fightful (fightful.com) - Free tier content + RSS

We scrape full article content, commentary, and analysis for educational
purposes and to enrich OWDB pages with properly attributed quotes and context.
All content is attributed to original sources with links.
"""

import logging
import re
import feedparser
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
            "rss": "https://www.wrestlinginc.com/feed/",
            "enabled": True,
        },
        "wrestlezone": {
            "url": "https://www.wrestlezone.com/news/",
            "rss": "https://www.wrestlezone.com/feed/",
            "enabled": True,
        },
        "pwtorch": {
            "url": "https://www.pwtorch.com/",
            "rss": "https://www.pwtorch.com/feed",
            "enabled": True,
        },
        "ringsidenews": {
            "url": "https://www.ringsidenews.com/",
            "rss": "https://www.ringsidenews.com/feed/",
            "enabled": True,
        },
        "fightful": {
            "url": "https://www.fightful.com/wrestling",
            "rss": "https://www.fightful.com/wrestling/feed",
            "enabled": True,
        },
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

    @retry_on_failure(max_retries=2)
    def scrape_rss_feed(self, source_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape news from RSS feed.
        Much more efficient than HTML scraping!

        Args:
            source_name: Key from NEWS_SOURCES dict
            limit: Max items to return

        Returns:
            List of news items with full content
        """
        if source_name not in self.NEWS_SOURCES:
            logger.error(f"Unknown news source: {source_name}")
            return []

        config = self.NEWS_SOURCES[source_name]
        rss_url = config.get("rss")

        if not rss_url:
            logger.warning(f"No RSS feed configured for {source_name}")
            return []

        try:
            # Parse RSS feed using feedparser
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                logger.warning(f"No entries found in RSS feed: {rss_url}")
                return []

            news_items = []

            for entry in feed.entries[:limit]:
                try:
                    # Extract basic info from RSS
                    headline = entry.get("title", "").strip()
                    article_url = entry.get("link", "")
                    published = entry.get("published_parsed") or entry.get("updated_parsed")

                    if not headline or not article_url:
                        continue

                    # Parse date
                    published_date = None
                    if published:
                        published_date = datetime(*published[:6]).strftime("%Y-%m-%d")

                    # Get summary/description from RSS (often truncated)
                    summary = entry.get("summary", "") or entry.get("description", "")
                    summary = self._clean_text(BeautifulSoup(summary, "lxml").get_text())

                    # Get full article content by fetching the page
                    full_content = None
                    author = entry.get("author", "")

                    try:
                        full_content = self.scrape_full_article(article_url)
                    except Exception as e:
                        logger.warning(f"Failed to fetch full article {article_url}: {e}")
                        # Continue with summary only

                    # Extract categories/tags
                    categories = []
                    if hasattr(entry, "tags"):
                        categories = [tag.get("term", "") for tag in entry.tags if tag.get("term")]

                    news_item = {
                        "source": source_name,
                        "headline": headline,
                        "url": article_url,
                        "published_date": published_date or datetime.now().strftime("%Y-%m-%d"),
                        "summary": summary,
                        "full_content": full_content,
                        "author": author,
                        "categories": categories,
                    }

                    news_items.append(news_item)
                    logger.debug(f"Scraped from RSS: {headline}")

                except Exception as e:
                    logger.warning(f"Failed to parse RSS entry: {e}")
                    continue

            logger.info(f"Scraped {len(news_items)} articles from {source_name} RSS feed")
            return news_items

        except Exception as e:
            logger.error(f"Failed to parse RSS feed {rss_url}: {e}")
            return []

    @retry_on_failure(max_retries=2)
    def scrape_full_article(self, url: str) -> Optional[str]:
        """
        Scrape full article content from a URL.

        Args:
            url: Article URL

        Returns:
            Full article text content (cleaned)
        """
        response = self.fetch(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, "lxml")

        # Remove unwanted elements
        for element in soup.find_all(["script", "style", "nav", "header", "footer", "aside", "iframe", "ad"]):
            element.decompose()

        # Try common article content selectors
        article_selectors = [
            "article",
            ".article-content",
            ".entry-content",
            ".post-content",
            ".content",
            'div[class*="article"]',
            'div[class*="post"]',
            'div[class*="entry"]',
            "#content",
        ]

        article_content = None
        for selector in article_selectors:
            if "." in selector or "#" in selector or "[" in selector:
                # CSS selector
                if selector.startswith("."):
                    article_content = soup.find(class_=selector[1:])
                elif selector.startswith("#"):
                    article_content = soup.find(id=selector[1:])
                else:
                    article_content = soup.select_one(selector)
            else:
                # Tag name
                article_content = soup.find(selector)

            if article_content:
                break

        if not article_content:
            # Fallback: get largest text block
            paragraphs = soup.find_all("p")
            if paragraphs:
                article_content = BeautifulSoup("", "lxml")
                for p in paragraphs:
                    article_content.append(p)

        if not article_content:
            return None

        # Extract text and clean
        text = article_content.get_text(separator="\n", strip=True)
        text = self._clean_text(text)

        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text if len(text) > 100 else None  # Only return if substantive

    def scrape_all_rss(self, per_source_limit: int = 10) -> List[Dict[str, Any]]:
        """
        Scrape news from all RSS feeds.
        More efficient than HTML scraping!

        Args:
            per_source_limit: Max articles per source

        Returns:
            Combined list of articles with full content
        """
        all_articles = []

        for source_name, config in self.NEWS_SOURCES.items():
            if not config.get("enabled", True):
                continue

            if not config.get("rss"):
                continue

            try:
                articles = self.scrape_rss_feed(source_name, limit=per_source_limit)
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Failed to scrape RSS for {source_name}: {e}")
                continue

        logger.info(f"Scraped total of {len(all_articles)} articles from all RSS feeds")
        return all_articles
