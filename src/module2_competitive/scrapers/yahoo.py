"""
Yahoo News Health scraper for native ads.
"""

import logging

from playwright.sync_api import Page

from .base import NativeAdScraperBase
from ..models import NativeAd

logger = logging.getLogger(__name__)

NICHE_URLS: dict[str, list[str]] = {
    "brain-health": [
        "https://news.yahoo.com/health/",
    ],
    "lung-health": [
        "https://news.yahoo.com/health/",
    ],
    "mens-health": [
        "https://news.yahoo.com/health/",
    ],
}


class YahooScraper(NativeAdScraperBase):
    """Scraper for Yahoo News Health — Taboola/Outbrain native ad placement."""

    @property
    def source_name(self) -> str:
        return "yahoo"

    @property
    def target_urls(self) -> list[str]:
        urls = NICHE_URLS.get(self.niche, [])
        return urls[:2] if urls else []

    def extract_from_dom(self, page: Page) -> list[NativeAd]:
        """
        DOM fallback: look for ad containers on Yahoo.
        Yahoo uses various widget types — look broadly for sponsored content.
        """
        ads = []
        try:
            page.wait_for_selector(
                "[class*='sponsored'], [data-ad], [class*='native'], [id*='taboola'], [id*='outbrain']",
                timeout=8000,
            )
        except Exception:
            logger.debug("[yahoo] Native ad container not found in DOM")
            return ads

        items = page.query_selector_all(
            "[class*='sponsored-item'], [class*='native-item'], [data-ylk*='sponsored']"
        )
        for i, item in enumerate(items):
            try:
                headline_el = item.query_selector(
                    "[class*='title'], h2, h3, a, [role='heading']"
                )
                link_el = item.query_selector("a")
                img_el = item.query_selector("img")

                headline = headline_el.inner_text().strip() if headline_el else ""
                landing_url = link_el.get_attribute("href") or "" if link_el else ""
                image_url = img_el.get_attribute("src") if img_el else None

                if not headline or not landing_url or len(headline) < 5:
                    continue

                ads.append(
                    NativeAd(
                        headline=headline,
                        image_url=image_url,
                        landing_url=landing_url,
                        source_site=self.source_name,
                        niche=self.niche,
                        ad_network="unknown",
                        position=i,
                        fingerprint=self._fingerprint(headline, landing_url),
                    )
                )
            except Exception as e:
                logger.debug(f"Item parse error: {e}")

        return ads
