"""
Quora Q&A scraper using Playwright or Apify.
"""

import logging
import os
import random
import time

from playwright.sync_api import sync_playwright

from ..models import NativeAd
from .apify_client import ApifyClient

logger = logging.getLogger(__name__)

# Quora questions per niche
QUORA_QUESTIONS = {
    "brain-health": [
        "How-can-I-improve-my-memory-and-focus",
        "What-are-the-best-supplements-for-brain-health",
        "How-do-I-get-rid-of-brain-fog",
    ],
    "lung-health": [
        "How-can-I-improve-my-lung-health",
        "What-are-the-best-supplements-for-respiratory-health",
    ],
    "mens-health": [
        "What-are-the-best-supplements-for-mens-health",
        "How-can-I-improve-my-energy-levels",
    ],
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class QuoraAnswerScraper:
    """Scrape Quora for winning answers and credibility patterns."""

    def __init__(self, niche: str):
        self.niche = niche
        self.questions = QUORA_QUESTIONS.get(niche, [])

    def scrape(self) -> list[NativeAd]:
        """Scrape Quora using Apify or Playwright."""
        all_ads = []

        # Try Apify first if enabled
        use_apify = os.environ.get("USE_APIFY", "false").lower() == "true"
        if use_apify:
            logger.info("[quora] Using Apify for scraping")
            apify = ApifyClient()
            if apify.enabled:
                all_ads.extend(self._scrape_with_apify(apify))
                if all_ads:
                    return all_ads[:25]
                logger.warning("[quora] Apify returned no results, falling back to Playwright")

        # Fallback to Playwright
        logger.info("[quora] Using Playwright for scraping")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1440, "height": 900},
            )
            page = context.new_page()

            for question in self.questions:
                logger.info(f"[quora] Scraping: {question}")
                try:
                    answers = self._scrape_question(page, question)
                    all_ads.extend(answers)
                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    logger.error(f"[quora] Error scraping '{question}': {e}")

            browser.close()

        logger.info(f"[quora] Total answers collected: {len(all_ads)}")
        return all_ads[:25]

    def _scrape_with_apify(self, apify: ApifyClient) -> list[NativeAd]:
        """Scrape using Apify."""
        ads = []

        for question in self.questions:
            try:
                url = f"https://www.quora.com/{question}"
                logger.info(f"[quora] Apify scraping: {url}")

                answers = apify.scrape_quora_answers(url, max_answers=4)

                for answer in answers:
                    try:
                        text = answer.get("text", "") if isinstance(answer, dict) else str(answer)
                        if not text or len(text) < 15:
                            continue

                        headline = text.split("\n")[0][:150]

                        ads.append(
                            NativeAd(
                                headline=headline,
                                landing_url=url,
                                source_site="quora",
                                niche=self.niche,
                                ad_network="quora",
                                fingerprint=self._fingerprint(headline),
                            )
                        )
                    except Exception as e:
                        logger.debug(f"[quora] Apify parse error: {e}")

            except Exception as e:
                logger.error(f"[quora] Apify error for '{question}': {e}")

        return ads

    def _scrape_question(self, page, question_slug: str) -> list[NativeAd]:
        """Scrape answers for a specific question."""
        answers = []

        try:
            url = f"https://www.quora.com/{question_slug}"
            page.goto(url, wait_until="domcontentloaded", timeout=10_000)
            page.wait_for_timeout(2000)

            # Try multiple selectors for answers
            selectors = [
                "[data-key*='answer']",  # Original
                "div[id*='answer_']",  # By ID pattern
                "div.spacing_item_container",  # Answer container class
                "div[class*='AnswerContent']",  # Answer content class
                "span[class*='AnswerText']",  # Answer text span
            ]

            answer_divs = []
            for selector in selectors:
                logger.debug(f"[quora] Trying selector: {selector}")
                found = page.query_selector_all(selector)
                if found:
                    logger.info(f"[quora] Found {len(found)} with selector: {selector}")
                    answer_divs = found
                    break

            if not answer_divs:
                # Log page structure for debugging
                page_title = page.title()
                body_snippet = page.content()[:500]
                logger.warning(f"[quora] No answers found. Title: {page_title}. Snippet: {body_snippet}")
                return answers

            for answer_div in answer_divs[:4]:
                try:
                    # Get answer text - try inner_text
                    answer_text = answer_div.inner_text()[:250]

                    if not answer_text or len(answer_text) < 15:
                        continue

                    # Create headline from answer
                    headline = answer_text.split("\n")[0][:150]

                    answers.append(
                        NativeAd(
                            headline=headline,
                            landing_url=url,
                            source_site="quora",
                            niche=self.niche,
                            ad_network="quora",
                            fingerprint=self._fingerprint(headline),
                        )
                    )

                except Exception as e:
                    logger.debug(f"[quora] Parse error: {e}")

        except Exception as e:
            logger.error(f"[quora] Load error: {e}")

        return answers

    def _fingerprint(self, text: str) -> str:
        """Create fingerprint for deduplication."""
        import hashlib
        return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:16]
