"""
Daily Mail US health/lifestyle native ad scraper.
Targets sections heavy with older US demographic content.
"""

import json
import logging
import random
import re
import time

import requests
from bs4 import BeautifulSoup

from ..models import NativeAd

logger = logging.getLogger(__name__)

NICHE_URLS: dict[str, list[str]] = {
    "brain-health": [
        "https://www.dailymail.co.uk/health/index.html",
    ],
    "lung-health": [
        "https://www.dailymail.co.uk/health/index.html",
    ],
    "mens-health": [
        "https://www.dailymail.co.uk/health/index.html",
    ],
}

FALLBACK_URLS = [
    "https://www.dailymail.co.uk/news/us/index.html",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


class DailyMailScraper:
    """Scraper for Daily Mail US — native ad extraction using requests + BeautifulSoup."""

    def __init__(self, niche: str):
        self.niche = niche
        self.source_name = "dailymail"

    def scrape(self) -> list[NativeAd]:
        """Scrape Daily Mail health articles as winning headlines."""
        all_ads: list[NativeAd] = []

        urls = NICHE_URLS.get(self.niche, FALLBACK_URLS)
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        for url in urls:
            logger.info(f"[dailymail] Scraping: {url}")
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")

                # Extract article headlines as "winning language"
                ads = self._extract_article_headlines(soup)
                logger.info(f"[dailymail] Found {len(ads)} article headlines from {url}")
                all_ads.extend(ads)

                time.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.warning(f"[dailymail] Error scraping {url}: {e}")

        return all_ads

    def _extract_article_headlines(self, soup: BeautifulSoup) -> list[NativeAd]:
        """
        Extract Daily Mail article headlines as winning native ad language.
        These headlines are optimized for clicks and engagement.
        """
        ads = []
        seen_urls = set()

        # Find all article links with headlines
        links = soup.find_all("a", href=re.compile(r"/health/article-"))

        for link in links:
            try:
                headline = link.get_text(strip=True)
                url = link.get("href", "").strip()

                # Filter for quality headlines
                if not headline or not url:
                    continue
                if len(headline) < 15 or len(headline) > 300:
                    continue
                if url in seen_urls:
                    continue

                # Make absolute URL
                if url.startswith("/"):
                    url = f"https://www.dailymail.co.uk{url}"

                seen_urls.add(url)

                ad = NativeAd(
                    headline=headline,
                    landing_url=url,
                    source_site=self.source_name,
                    niche=self.niche,
                    ad_network="native",
                    fingerprint=self._fingerprint(headline, url),
                )
                ads.append(ad)

                if len(ads) >= 30:  # Limit to 30 articles
                    break

            except Exception as e:
                logger.debug(f"[dailymail] Error parsing link: {e}")
                continue

        return ads

    @staticmethod
    def _fingerprint(headline: str, url: str) -> str:
        """Create unique fingerprint for deduplication."""
        import hashlib
        from urllib.parse import urlparse

        domain = urlparse(url).netloc
        raw = f"{headline.lower().strip()}|{domain}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
