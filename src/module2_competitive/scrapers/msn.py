"""
MSN Health scraper for native ads.
"""

import logging

from playwright.sync_api import Page

from .base import NativeAdScraperBase
from ..models import NativeAd

logger = logging.getLogger(__name__)

NICHE_URLS: dict[str, list[str]] = {
    "brain-health": [
        "https://www.msn.com/en-us/health",
    ],
    "lung-health": [
        "https://www.msn.com/en-us/health",
    ],
    "mens-health": [
        "https://www.msn.com/en-us/health",
    ],
}


class MSNScraper(NativeAdScraperBase):
    """Scraper for MSN Health — Outbrain native ad placement."""

    @property
    def source_name(self) -> str:
        return "msn"

    @property
    def target_urls(self) -> list[str]:
        urls = NICHE_URLS.get(self.niche, [])
        return urls[:2] if urls else []

    def extract_from_dom(self, page: Page) -> list[NativeAd]:
        """
        DOM fallback: look for Outbrain widget containers.
        Outbrain on MSN uses: .ob-widget, .ob-dynamic-rec-container
        """
        ads = []
        try:
            page.wait_for_selector(
                ".ob-widget, .ob-dynamic-rec-container, [class*='outbrain']",
                timeout=8000,
            )
        except Exception:
            logger.debug("[msn] Outbrain container not found in DOM")
            return ads

        items = page.query_selector_all(
            ".ob-rec-text, .ob-dynamic-rec-container [role='link'], [class*='ob-rec']"
        )
        for i, item in enumerate(items):
            try:
                headline_el = item.query_selector(".ob-rec-title, [class*='title']")
                link_el = item.query_selector("a")
                img_el = item.query_selector("img")

                headline = headline_el.inner_text().strip() if headline_el else ""
                landing_url = link_el.get_attribute("href") or "" if link_el else ""
                image_url = img_el.get_attribute("src") if img_el else None

                if not headline or not landing_url:
                    continue

                ads.append(
                    NativeAd(
                        headline=headline,
                        image_url=image_url,
                        landing_url=landing_url,
                        source_site=self.source_name,
                        niche=self.niche,
                        ad_network="outbrain",
                        position=i,
                        fingerprint=self._fingerprint(headline, landing_url),
                    )
                )
            except Exception as e:
                logger.debug(f"Item parse error: {e}")

        return ads
