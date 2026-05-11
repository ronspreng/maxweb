"""
Scrape competitor affiliate landing pages for headlines, angles, CTAs.
"""

import logging
import re
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from ..models import NativeAd

logger = logging.getLogger(__name__)

# Search queries per niche to find affiliate landing pages
SEARCH_QUERIES = {
    "brain-health": [
        "brain health supplement review site:com",
        "memory supplement landing page",
        "cognitive enhancement presell",
    ],
    "lung-health": [
        "lung health supplement review site:com",
        "respiratory support landing page",
    ],
    "mens-health": [
        "mens health supplement review site:com",
        "testosterone support presell",
    ],
}


class AffiliateLandingPageScraper:
    """Scrape competitor affiliate landing pages for winning angles."""

    def __init__(self, niche: str):
        self.niche = niche
        self.search_queries = SEARCH_QUERIES.get(niche, [])

    def scrape(self) -> list[NativeAd]:
        """Search Google for affiliate LPs and scrape them."""
        all_ads = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            for query in self.search_queries:
                logger.info(f"[affiliate_lp] Searching: {query}")

                try:
                    # Go to Google
                    page.goto("https://www.google.com", wait_until="networkidle")
                    page.wait_for_timeout(1000)

                    # Search
                    page.fill("textarea[aria-label='Search']", query)
                    page.press("textarea[aria-label='Search']", "Enter")
                    page.wait_for_timeout(3000)

                    # Get search results
                    links = page.query_selector_all("a[jsname]")
                    urls = []

                    for link in links[:5]:
                        try:
                            href = link.get_attribute("href")
                            if href and "google.com" not in href and href.startswith("http"):
                                urls.append(href)
                        except:
                            pass

                    # Scrape each URL
                    for url in urls[:3]:
                        logger.info(f"[affiliate_lp] Scraping: {url}")
                        ads = self._scrape_landing_page(page, url)
                        all_ads.extend(ads)

                except Exception as e:
                    logger.error(f"[affiliate_lp] Error searching '{query}': {e}")

            browser.close()

        logger.info(f"[affiliate_lp] Total headlines collected: {len(all_ads)}")
        return all_ads[:30]

    def _scrape_landing_page(self, page, url: str) -> list[NativeAd]:
        """Scrape headlines and CTAs from a landing page."""
        ads = []

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15_000)
            page.wait_for_timeout(2000)

            # Extract main headline
            headline_selectors = [
                "h1",
                "[class*='headline']",
                "[class*='title']",
                "[class*='hero'] h1",
            ]

            headlines = set()
            for selector in headline_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for el in elements:
                        text = el.inner_text().strip()
                        if text and len(text) > 15 and len(text) < 200:
                            headlines.add(text)
                except:
                    pass

            # Extract CTAs
            ctas = set()
            cta_selectors = [
                "button",
                "[class*='cta']",
                "[class*='button-primary']",
            ]

            for selector in cta_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for el in elements:
                        text = el.inner_text().strip()
                        if text and len(text) < 50:
                            ctas.add(text)
                except:
                    pass

            # Create NativeAd objects from headlines
            for headline in headlines:
                ads.append(
                    NativeAd(
                        headline=headline,
                        landing_url=url,
                        source_site="affiliate_lp",
                        niche=self.niche,
                        ad_network="affiliate_page",
                        fingerprint=self._fingerprint(headline),
                        metadata={"ctas": list(ctas)[:3]},
                    )
                )

            logger.info(f"[affiliate_lp] {url}: {len(ads)} headlines extracted")

        except Exception as e:
            logger.debug(f"[affiliate_lp] Error scraping {url}: {e}")

        return ads

    def _fingerprint(self, text: str) -> str:
        """Create fingerprint for deduplication."""
        import hashlib
        return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:16]
