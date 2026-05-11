"""
Daily Mail US health/lifestyle native ad scraper.
Targets sections heavy with older US demographic content.
"""

import logging

from playwright.sync_api import Page

from .base import NativeAdScraperBase
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


class DailyMailScraper(NativeAdScraperBase):
    """Scraper for Daily Mail US — heavy Taboola native ad placement."""

    @property
    def source_name(self) -> str:
        return "dailymail"

    @property
    def target_urls(self) -> list[str]:
        urls = NICHE_URLS.get(self.niche, FALLBACK_URLS)
        return urls[:2]

    def extract_from_dom(self, page: Page) -> list[NativeAd]:
        """
        DOM fallback: look for Taboola widget containers.
        Taboola on DailyMail uses: div[id^='taboola-'] > .trc_rbox_div .thumbnails-item
        """
        ads = []
        try:
            page.wait_for_selector(
                "[id^='taboola-'] .thumbnails-item, .trc-content-sponsored",
                timeout=8000,
            )
        except Exception:
            logger.debug("[dailymail] Taboola container not found in DOM")
            return ads

        items = page.query_selector_all(".thumbnails-item, .trc-content-sponsored")
        for i, item in enumerate(items):
            try:
                headline_el = item.query_selector(".trc-item-title, [class*='title']")
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
                        ad_network="taboola",
                        position=i,
                        fingerprint=self._fingerprint(headline, landing_url),
                    )
                )
            except Exception as e:
                logger.debug(f"Item parse error: {e}")

        return ads
