"""
Amazon product reviews scraper using Playwright or Apify.
"""

import logging
import os
import random
import time

from playwright.sync_api import sync_playwright

from ..models import NativeAd
from .apify_client import ApifyClient

logger = logging.getLogger(__name__)

# Search queries to find relevant products on Amazon
SEARCH_QUERIES = {
    "brain-health": [
        "best brain health supplement",
        "memory supplement reviews",
        "nootropic stack",
    ],
    "lung-health": [
        "lung health supplement",
        "respiratory support supplement",
    ],
    "mens-health": [
        "mens health supplement",
        "testosterone support reviews",
    ],
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class AmazonReviewsScraper:
    """Scrape Amazon product reviews for customer pain points and language."""

    def __init__(self, niche: str):
        self.niche = niche
        self.search_queries = SEARCH_QUERIES.get(niche, [])

    def scrape(self) -> list[NativeAd]:
        """Scrape Amazon reviews using Apify or Playwright."""
        all_ads = []

        # Try Apify first if enabled
        use_apify = os.environ.get("USE_APIFY", "false").lower() == "true"
        if use_apify:
            logger.info("[amazon] Using Apify for scraping")
            apify = ApifyClient()
            if apify.enabled:
                all_ads.extend(self._scrape_with_apify(apify))
                if all_ads:
                    return all_ads[:30]
                logger.warning("[amazon] Apify returned no results, falling back to Playwright")

        # Fallback to Playwright
        logger.info("[amazon] Using Playwright for scraping")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1440, "height": 900},
                locale="en-US",
            )
            page = context.new_page()

            for query in self.search_queries[:2]:
                logger.info(f"[amazon] Searching: {query}")
                try:
                    reviews = self._scrape_query(page, query)
                    all_ads.extend(reviews)
                    time.sleep(random.uniform(2, 4))  # Rate limit
                except Exception as e:
                    logger.error(f"[amazon] Error searching '{query}': {e}")

            browser.close()

        logger.info(f"[amazon] Total reviews collected: {len(all_ads)}")
        return all_ads[:30]

    def _scrape_with_apify(self, apify: ApifyClient) -> list[NativeAd]:
        """Scrape using Apify actor."""
        ads = []

        for query in self.search_queries[:2]:
            try:
                # Build Amazon search URL
                search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
                logger.info(f"[amazon] Apify searching: {search_url}")

                # Apify returns reviews directly from a product
                # We need to get a product URL first, then scrape reviews
                # For now, construct a direct reviews search
                reviews = apify.scrape_amazon_reviews(search_url, max_reviews=5)

                for review in reviews:
                    try:
                        title = review.get("title", "") if isinstance(review, dict) else str(review)
                        if not title or len(title) < 5:
                            continue

                        ads.append(
                            NativeAd(
                                headline=title[:200],
                                landing_url=search_url,
                                source_site="amazon",
                                niche=self.niche,
                                ad_network="amazon",
                                fingerprint=self._fingerprint(title),
                            )
                        )
                    except Exception as e:
                        logger.debug(f"[amazon] Apify parse error: {e}")

            except Exception as e:
                logger.error(f"[amazon] Apify error for '{query}': {e}")

        return ads

    def _scrape_query(self, page, query: str) -> list[NativeAd]:
        """Scrape reviews for a search query."""
        reviews = []

        try:
            search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
            logger.debug(f"[amazon] Navigating to: {search_url}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(2000)

            # Get first product link
            product_links = page.query_selector_all("h2 a")
            logger.info(f"[amazon] Found {len(product_links)} product links in search results")

            if product_links:
                product_url = product_links[0].get_attribute("href")
                logger.info(f"[amazon] First product URL: {product_url}")
                if product_url:
                    if not product_url.startswith("http"):
                        product_url = f"https://www.amazon.com{product_url}"
                    logger.info(f"[amazon] Scraping reviews from: {product_url}")
                    reviews = self._scrape_reviews_page(page, product_url)
            else:
                logger.warning(f"[amazon] No product links found for query: {query}")

        except Exception as e:
            logger.error(f"[amazon] Search error: {e}")

        return reviews

    def _scrape_reviews_page(self, page, product_url: str) -> list[NativeAd]:
        """Scrape reviews from product reviews page."""
        reviews = []

        try:
            reviews_url = product_url.replace("/dp/", "/product-reviews/") if "/dp/" in product_url else product_url + "/reviews"
            logger.info(f"[amazon] Navigating to reviews page: {reviews_url}")
            page.goto(reviews_url, wait_until="domcontentloaded", timeout=15_000)
            page.wait_for_timeout(2000)

            # Try multiple selectors in order of likelihood
            selectors = [
                "[data-hook='review']",  # Standard Amazon
                "div[data-component-type='s-search-result']",  # Alternative
                "div.a-section.reviewCard",  # Review card class
                "div[id^='customer-review-']",  # By ID pattern
                "span.a-size-base.review-text",  # Review text span
            ]

            review_elements = []
            for selector in selectors:
                logger.debug(f"[amazon] Trying selector: {selector}")
                found = page.query_selector_all(selector)
                if found:
                    logger.info(f"[amazon] Found {len(found)} with selector: {selector}")
                    review_elements = found
                    break

            if not review_elements:
                # Log page structure for debugging
                body_text = page.content()[:1000]
                logger.warning(f"[amazon] No reviews found. Page snippet: {body_text}")
                return reviews

            for review in review_elements[:5]:
                try:
                    # Try different title selectors
                    title = ""
                    for title_sel in ["[data-hook='review-title']", "a.a-size-base", "span.a-size-base"]:
                        title_elem = review.query_selector(title_sel) if hasattr(review, 'query_selector') else None
                        if title_elem:
                            title = title_elem.inner_text()
                            break

                    # Try different body selectors
                    body = ""
                    for body_sel in ["[data-hook='review-body']", "span.a-size-base.review-text"]:
                        body_elem = review.query_selector(body_sel) if hasattr(review, 'query_selector') else None
                        if body_elem:
                            body = body_elem.inner_text()[:120]
                            break

                    if not title or len(title) < 5:
                        continue

                    headline = f"{title} - {body}" if body else title

                    reviews.append(
                        NativeAd(
                            headline=headline[:200],
                            landing_url=product_url,
                            source_site="amazon",
                            niche=self.niche,
                            ad_network="amazon",
                            fingerprint=self._fingerprint(headline),
                        )
                    )

                except Exception as e:
                    logger.debug(f"[amazon] Parse error: {e}")

        except Exception as e:
            logger.error(f"[amazon] Reviews page error: {e}")

        return reviews

    def _fingerprint(self, text: str) -> str:
        """Create fingerprint for deduplication."""
        import hashlib
        return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:16]
