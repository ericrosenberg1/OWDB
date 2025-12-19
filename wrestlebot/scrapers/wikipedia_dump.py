"""
Wikipedia Dump Processor

Downloads and processes Wikipedia database dumps to extract
wrestling data in bulk without rate limits.
"""

import logging
import requests
import bz2
import xml.etree.ElementTree as ET
from typing import List, Dict, Generator
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class WikipediaDumpProcessor:
    """Process Wikipedia dumps for bulk wrestling data extraction."""

    # Latest Wikipedia dumps (updated monthly)
    DUMP_URL = "https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream.xml.bz2"
    DUMP_INDEX_URL = "https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream-index.txt.bz2"

    # Wrestling-related keywords for filtering
    WRESTLING_KEYWORDS = [
        'professional wrestler',
        'wrestling',
        'WWE',
        'WWF',
        'WCW',
        'ECW',
        'AEW',
        'NJPW',
        'Impact Wrestling',
        'TNA',
        'Ring of Honor',
        'ROH',
        'Lucha Libre',
        'NWA',
        'CMLL',
        'AAA',
    ]

    def __init__(self, cache_dir: str = "/tmp/wikipedia_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.dump_path = self.cache_dir / "enwiki-latest.xml.bz2"
        self.index_path = self.cache_dir / "enwiki-latest-index.txt.bz2"

    def download_dump(self, force: bool = False) -> bool:
        """Download Wikipedia dump if not cached."""
        if self.dump_path.exists() and not force:
            logger.info(f"Wikipedia dump already cached at {self.dump_path}")
            return True

        logger.info(f"Downloading Wikipedia dump from {self.DUMP_URL}")
        logger.warning("This is a LARGE file (~20GB compressed). This will take a while...")

        try:
            response = requests.get(self.DUMP_URL, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(self.dump_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if downloaded % (100 * 1024 * 1024) == 0:  # Every 100MB
                            logger.info(f"Downloaded {downloaded / (1024**3):.2f} GB")

            logger.info(f"Download complete: {self.dump_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download Wikipedia dump: {e}")
            if self.dump_path.exists():
                self.dump_path.unlink()
            return False

    def is_wrestling_article(self, text: str, title: str) -> bool:
        """Check if article is wrestling-related."""
        text_lower = text.lower()
        title_lower = title.lower()

        # Check title first (faster)
        for keyword in self.WRESTLING_KEYWORDS:
            if keyword.lower() in title_lower:
                return True

        # Check content (first 2000 chars)
        content_sample = text_lower[:2000]
        keyword_count = sum(1 for kw in self.WRESTLING_KEYWORDS if kw.lower() in content_sample)

        return keyword_count >= 2  # At least 2 wrestling keywords

    def extract_wrestler_data(self, title: str, text: str) -> Dict:
        """Extract wrestler data from Wikipedia article text."""
        # Basic extraction - can be enhanced with more sophisticated parsing
        slug = title.lower().replace(' ', '-').replace("'", '')
        for suffix in ['_(wrestler)', '_(professional_wrestler)']:
            if slug.endswith(suffix.replace('_', '-')):
                slug = slug[:-len(suffix)]

        data = {
            'name': title.replace(' (wrestler)', '').replace(' (professional wrestler)', ''),
            'slug': slug,
            'about': text[:1000],  # First 1000 chars
            'wikipedia_url': f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        }

        # Extract debut year
        debut_match = re.search(r'debut(?:ed)?\s+(?:in\s+)?(\d{4})', text[:5000], re.IGNORECASE)
        if debut_match:
            data['debut_year'] = int(debut_match.group(1))

        # Extract birth year
        birth_match = re.search(r'born[^\d]*(\d{4})', text[:2000], re.IGNORECASE)
        if birth_match:
            year = int(birth_match.group(1))
            if 1850 < year < 2020:  # Sanity check
                data['birth_year'] = year

        return data

    def process_dump_stream(self, max_articles: int = 10000) -> Generator[Dict, None, None]:
        """Process Wikipedia dump and yield wrestling-related articles."""
        if not self.dump_path.exists():
            logger.error("Wikipedia dump not found. Run download_dump() first.")
            return

        logger.info(f"Processing Wikipedia dump for wrestling articles (max: {max_articles})")

        found_count = 0
        processed_count = 0

        try:
            with bz2.open(self.dump_path, 'rt', encoding='utf-8') as f:
                # Parse XML stream
                current_title = None
                current_text = []
                in_text = False

                for line in f:
                    processed_count += 1

                    if '<title>' in line:
                        current_title = line.split('<title>')[1].split('</title>')[0]

                    elif '<text' in line:
                        in_text = True
                        current_text = [line]

                    elif in_text:
                        current_text.append(line)

                        if '</text>' in line:
                            in_text = False
                            text = ''.join(current_text)

                            # Check if wrestling-related
                            if current_title and self.is_wrestling_article(text, current_title):
                                wrestler_data = self.extract_wrestler_data(current_title, text)
                                found_count += 1
                                logger.info(f"Found wrestling article #{found_count}: {current_title}")
                                yield wrestler_data

                                if found_count >= max_articles:
                                    logger.info(f"Reached max articles limit: {max_articles}")
                                    return

                            current_title = None
                            current_text = []

                    if processed_count % 100000 == 0:
                        logger.info(f"Processed {processed_count} lines, found {found_count} wrestling articles")

        except Exception as e:
            logger.error(f"Error processing dump: {e}")

        logger.info(f"Processing complete: found {found_count} wrestling articles from {processed_count} lines")
