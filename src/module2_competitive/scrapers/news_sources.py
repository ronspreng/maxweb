"""
Health news scraper supporting multiple news sources via requests.
Focuses on health/wellness articles as competitive intelligence.
"""

import hashlib
import logging
import random
import re
import time
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup

from ..models import NativeAd

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


class NewsSourceScraper(ABC):
    """Base class for news source scrapers."""

    def __init__(self, niche: str):
        self.niche = niche

    @abstractmethod
    def get_urls(self) -> list[str]:
        """Return URLs to scrape for this niche."""
        pass

    @abstractmethod
    def extract_articles(self, soup: BeautifulSoup) -> list[NativeAd]:
        """Extract articles from BeautifulSoup parsed HTML."""
        pass

    def scrape(self) -> list[NativeAd]:
        """Scrape news articles using requests + BeautifulSoup."""
        all_ads = []
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        for url in self.get_urls():
            logger.info(f"[{self.__class__.__name__}] Scraping: {url}")
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")
                articles = self.extract_articles(soup)

                logger.info(f"[{self.__class__.__name__}] Found {len(articles)} articles from {url}")
                all_ads.extend(articles)

                time.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}] Error scraping {url}: {e}")

        return all_ads

    @staticmethod
    def _fingerprint(headline: str, url: str) -> str:
        """Create unique fingerprint for deduplication."""
        domain = url.split("/")[2] if url.startswith("http") else "unknown"
        raw = f"{headline.lower().strip()}|{domain}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class BBCScraper(NewsSourceScraper):
    """Scrape BBC Health articles."""

    def get_urls(self) -> list[str]:
        return ["https://www.bbc.com/news/health"]

    def extract_articles(self, soup: BeautifulSoup) -> list[NativeAd]:
        ads = []
        links = soup.find_all("a", href=re.compile(r"/news/health"))

        for link in links[:20]:
            try:
                headline = link.get_text(strip=True)
                url = link.get("href", "").strip()

                if not headline or not url:
                    continue
                if len(headline) < 15 or len(headline) > 300:
                    continue

                if url.startswith("/"):
                    url = f"https://www.bbc.com{url}"

                ad = NativeAd(
                    headline=headline,
                    landing_url=url,
                    source_site="bbc",
                    niche=self.niche,
                    ad_network="native",
                    fingerprint=self._fingerprint(headline, url),
                )
                ads.append(ad)

            except Exception as e:
                logger.debug(f"[BBC] Parse error: {e}")

        return ads


class GuardianScraper(NewsSourceScraper):
    """Scrape The Guardian health articles."""

    def get_urls(self) -> list[str]:
        return ["https://www.theguardian.com/science/health"]

    def extract_articles(self, soup: BeautifulSoup) -> list[NativeAd]:
        ads = []
        links = soup.find_all("a", href=re.compile(r"/science/health|/lifeandstyle/health"))

        for link in links[:20]:
            try:
                headline = link.get_text(strip=True)
                url = link.get("href", "").strip()

                if not headline or not url:
                    continue
                if len(headline) < 15 or len(headline) > 300:
                    continue

                if not url.startswith("http"):
                    url = f"https://www.theguardian.com{url}"

                ad = NativeAd(
                    headline=headline,
                    landing_url=url,
                    source_site="guardian",
                    niche=self.niche,
                    ad_network="native",
                    fingerprint=self._fingerprint(headline, url),
                )
                ads.append(ad)

            except Exception as e:
                logger.debug(f"[Guardian] Parse error: {e}")

        return ads


class NPRScraper(NewsSourceScraper):
    """Scrape NPR health articles."""

    def get_urls(self) -> list[str]:
        return ["https://www.npr.org/sections/health-shots"]

    def extract_articles(self, soup: BeautifulSoup) -> list[NativeAd]:
        ads = []
        links = soup.find_all("a", href=re.compile(r"/sections/health|/health-shots"))

        for link in links[:25]:
            try:
                headline = link.get_text(strip=True)
                url = link.get("href", "").strip()

                if not headline or not url:
                    continue
                if len(headline) < 15 or len(headline) > 300:
                    continue

                if url.startswith("/"):
                    url = f"https://www.npr.org{url}"

                ad = NativeAd(
                    headline=headline,
                    landing_url=url,
                    source_site="npr",
                    niche=self.niche,
                    ad_network="native",
                    fingerprint=self._fingerprint(headline, url),
                )
                ads.append(ad)

            except Exception as e:
                logger.debug(f"[NPR] Parse error: {e}")

        return ads


class HealthLineScraper(NewsSourceScraper):
    """Scrape Healthline articles."""

    def get_urls(self) -> list[str]:
        return ["https://www.healthline.com/"]

    def extract_articles(self, soup: BeautifulSoup) -> list[NativeAd]:
        ads = []
        links = soup.find_all("a", href=re.compile(r"^/health/|^https://www.healthline.com/health/"))

        for link in links[:25]:
            try:
                headline = link.get_text(strip=True)
                url = link.get("href", "").strip()

                if not headline or not url:
                    continue
                if len(headline) < 15 or len(headline) > 300:
                    continue

                if not url.startswith("http"):
                    url = f"https://www.healthline.com{url}"

                ad = NativeAd(
                    headline=headline,
                    landing_url=url,
                    source_site="healthline",
                    niche=self.niche,
                    ad_network="native",
                    fingerprint=self._fingerprint(headline, url),
                )
                ads.append(ad)

            except Exception as e:
                logger.debug(f"[Healthline] Parse error: {e}")

        return ads


class MedicalNewsTodayScraper(NewsSourceScraper):
    """Scrape Medical News Today articles."""

    def get_urls(self) -> list[str]:
        return ["https://www.medicalnewstoday.com/"]

    def extract_articles(self, soup: BeautifulSoup) -> list[NativeAd]:
        ads = []
        links = soup.find_all("a", href=re.compile(r"article|articles"))

        for link in links[:25]:
            try:
                headline = link.get_text(strip=True)
                url = link.get("href", "").strip()

                if not headline or not url:
                    continue
                if len(headline) < 15 or len(headline) > 300:
                    continue

                if not url.startswith("http"):
                    url = f"https://www.medicalnewstoday.com{url}"

                ad = NativeAd(
                    headline=headline,
                    landing_url=url,
                    source_site="medicalnewstoday",
                    niche=self.niche,
                    ad_network="native",
                    fingerprint=self._fingerprint(headline, url),
                )
                ads.append(ad)

            except Exception as e:
                logger.debug(f"[MedicalNewsToday] Parse error: {e}")

        return ads
