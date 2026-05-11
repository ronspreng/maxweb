"""
Abstract base scraper for native ad extraction.
"""

import hashlib
import json
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urlparse

from playwright.sync_api import Page, Route, sync_playwright

from ..models import NativeAd

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

TABOOLA_API_PATTERN = "**/api.taboola.com/**recommendations*"
OUTBRAIN_API_PATTERN = "**/widgets.outbrain.com/api/**"


class NativeAdScraperBase(ABC):
    """Base class for all native ad site scrapers."""

    def __init__(self, niche: str, rate_limit_seconds: tuple[float, float] = (5.0, 10.0)):
        self.niche = niche
        self.rate_limit_seconds = rate_limit_seconds
        self._intercepted_ads: list[NativeAd] = []

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this scraper source (e.g. 'dailymail')."""
        ...

    @property
    @abstractmethod
    def target_urls(self) -> list[str]:
        """Return list of article/section URLs to scrape for this niche."""
        ...

    @abstractmethod
    def extract_from_dom(self, page: Page) -> list[NativeAd]:
        """Extract ads from DOM after page load. Fallback if interception yields nothing."""
        ...

    def scrape(self) -> list[NativeAd]:
        """Main entry point. Returns deduplicated list of NativeAd objects."""
        all_ads: list[NativeAd] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="America/New_York",
            )
            page = context.new_page()

            self._setup_route_interception(page)

            for url in self.target_urls:
                logger.info(f"[{self.source_name}] Scraping: {url}")
                self._intercepted_ads.clear()

                try:
                    page.goto(url, wait_until="networkidle", timeout=30_000)
                    page.wait_for_timeout(3000)

                    if self._intercepted_ads:
                        logger.info(
                            f"[{self.source_name}] Intercepted {len(self._intercepted_ads)} ads via network"
                        )
                        all_ads.extend(self._intercepted_ads)
                    else:
                        dom_ads = self.extract_from_dom(page)
                        logger.info(
                            f"[{self.source_name}] Extracted {len(dom_ads)} ads from DOM"
                        )
                        all_ads.extend(dom_ads)

                except Exception as e:
                    logger.warning(f"[{self.source_name}] Failed on {url}: {e}")

                delay = random.uniform(*self.rate_limit_seconds)
                logger.debug(f"Sleeping {delay:.1f}s")
                time.sleep(delay)

            browser.close()

        return all_ads

    def _setup_route_interception(self, page: Page) -> None:
        """Intercept Taboola/Outbrain API calls to capture ads as clean JSON."""

        def handle_taboola(route: Route) -> None:
            response = route.fetch()
            try:
                data = response.json()
                ads = self._parse_taboola_response(data)
                self._intercepted_ads.extend(ads)
            except Exception as e:
                logger.debug(f"Taboola parse error: {e}")
            finally:
                route.fulfill(response=response)

        def handle_outbrain(route: Route) -> None:
            response = route.fetch()
            try:
                data = response.json()
                ads = self._parse_outbrain_response(data)
                self._intercepted_ads.extend(ads)
            except Exception as e:
                logger.debug(f"Outbrain parse error: {e}")
            finally:
                route.fulfill(response=response)

        page.route(TABOOLA_API_PATTERN, handle_taboola)
        page.route(OUTBRAIN_API_PATTERN, handle_outbrain)

    def _parse_taboola_response(self, data: dict) -> list[NativeAd]:
        """Parse Taboola recommendations API response."""
        ads = []
        for item in data.get("list", []):
            headline = item.get("name", "").strip()
            if not headline:
                continue
            thumbnails = item.get("thumbnail", [])
            image_url = thumbnails[0].get("url") if thumbnails else None
            landing_url = item.get("url", "")
            if not landing_url:
                continue
            ads.append(
                NativeAd(
                    headline=headline,
                    image_url=image_url,
                    landing_url=landing_url,
                    source_site=self.source_name,
                    niche=self.niche,
                    ad_network="taboola",
                    fingerprint=self._fingerprint(headline, landing_url),
                )
            )
        return ads

    def _parse_outbrain_response(self, data: dict) -> list[NativeAd]:
        """Parse Outbrain recommendations API response."""
        ads = []
        for rec in data.get("recommendations", []):
            content = rec.get("content", {})
            headline = content.get("title", "").strip()
            landing_url = content.get("url", "")
            if not headline or not landing_url:
                continue
            image_url = content.get("thumbnail", {}).get("url")
            ads.append(
                NativeAd(
                    headline=headline,
                    image_url=image_url,
                    landing_url=landing_url,
                    source_site=self.source_name,
                    niche=self.niche,
                    ad_network="outbrain",
                    fingerprint=self._fingerprint(headline, landing_url),
                )
            )
        return ads

    @staticmethod
    def _fingerprint(headline: str, url: str) -> str:
        """SHA256 fingerprint of normalized headline + domain for dedup."""
        domain = urlparse(url).netloc
        raw = f"{headline.lower().strip()}|{domain}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
