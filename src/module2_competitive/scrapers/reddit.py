"""
Reddit health niches scraper for pain points and winning language patterns.
"""

import json
import logging
import re
import time
from typing import Optional

import requests
from playwright.sync_api import Page, sync_playwright

from ..models import NativeAd

logger = logging.getLogger(__name__)

NICHE_SUBREDDITS = {
    "brain-health": ["Nootropics", "Cognition", "Productivity", "BrainFog"],
    "lung-health": ["Asthma", "Breathing", "Pulmonary", "RespiratoryHealth"],
    "mens-health": ["MentalHealth", "FitnessandNutrition", "Testosterone", "MenHealth"],
}

# Keyword → subreddit mappings for fallback
KEYWORD_SUBREDDITS = {
    "joint": ["JointHealth", "Arthritis", "Fitness"],
    "supplement": ["Supplements", "Health", "HealthAdvice"],
    "memory": ["Nootropics", "Cognition", "BrainFog"],
    "brain": ["Nootropics", "Cognition", "Productivity"],
    "health": ["Health", "HealthAdvice", "Medicine"],
    "fitness": ["Fitness", "FitnessandNutrition"],
    "diabetes": ["Diabetes", "Health", "HealthAdvice"],
    "lung": ["Asthma", "Breathing", "RespiratoryHealth"],
    "sleep": ["sleep", "insomnia", "Health"],
    "weight": ["loseit", "EatCheapAndHealthy", "FitnessandNutrition"],
}

# Generic fallback
GENERIC_SUBREDDITS = ["Health", "HealthAdvice", "Medicine", "AskDocs"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


class RedditScraper:
    """Scrape Reddit posts for health pain points and winning language."""

    def __init__(self, niche: str, keywords: list[str] | None = None):
        self.niche = niche

        # Use hardcoded subreddits if niche is mapped
        if niche in NICHE_SUBREDDITS:
            self.subreddits = NICHE_SUBREDDITS[niche]
        else:
            # Fallback: try to find subreddits from keywords
            subreddits_set = set()
            if keywords:
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in KEYWORD_SUBREDDITS:
                        subreddits_set.update(KEYWORD_SUBREDDITS[keyword_lower])

            # If no keywords matched, use generic subreddits
            if subreddits_set:
                self.subreddits = list(subreddits_set)[:6]  # Limit to 6
            else:
                self.subreddits = GENERIC_SUBREDDITS

    def scrape(self) -> list[NativeAd]:
        """Scrape Reddit posts and convert to NativeAd objects."""
        all_ads = []

        for i, subreddit in enumerate(self.subreddits):
            if i > 0:
                # Rate limit: wait between requests to avoid 429/500 errors
                time.sleep(2)

            logger.info(f"[reddit] Scraping /r/{subreddit}")
            posts = self._scrape_subreddit(subreddit)
            all_ads.extend(posts)

        logger.info(f"[reddit] Total posts collected: {len(all_ads)}")
        return all_ads[:50]  # Top 50 posts

    def _scrape_subreddit(self, subreddit: str) -> list[NativeAd]:
        """Scrape a single subreddit using browser automation to bypass blocks."""
        ads = []

        try:
            with sync_playwright() as p:
                # Use browser to bypass API blocks
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = context.new_page()

                url = f"https://www.reddit.com/r/{subreddit}/top/?t=month"
                logger.info(f"[reddit] Loading {url}")

                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                except:
                    # If page times out, try without waiting for network
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)

                # Wait for posts to load
                time.sleep(2)

                # Extract posts from page
                posts = page.locator('h3').all()

                for post_element in posts[:30]:
                    try:
                        title = post_element.text_content().strip()

                        if not title or len(title) < 10:
                            continue

                        # Extract pain points
                        pain_points = self._extract_pain_points(title)
                        if not pain_points:
                            continue

                        # Find parent post link
                        post_link = post_element.locator("xpath=ancestor::a[1]")
                        href = post_link.get_attribute("href") or ""

                        if not href.startswith("/r/"):
                            continue

                        ads.append(
                            NativeAd(
                                headline=title,
                                landing_url=f"https://reddit.com{href}",
                                source_site="reddit",
                                niche=self.niche,
                                ad_network="reddit",
                                fingerprint=self._fingerprint(title),
                                metadata={
                                    "subreddit": subreddit,
                                    "pain_points": pain_points,
                                },
                            )
                        )
                    except Exception as e:
                        logger.debug(f"[reddit] Error parsing post: {e}")
                        continue

                browser.close()
                logger.info(f"[reddit] /r/{subreddit}: {len(ads)} posts collected")

        except Exception as e:
            logger.error(f"[reddit] Error scraping /r/{subreddit}: {e}")

        return ads

    def _extract_pain_points(self, text: str) -> list[str]:
        """Extract pain points and triggers from text."""
        pain_patterns = [
            r"(?:struggling|suffering|struggling with|dealing with|problem with|issue with|can't|unable to|difficulty)",
            r"(?:help|advice|tips|how to|what works)",
            r"(?:anxiety|depression|stress|brain fog|fatigue|tired|exhausted)",
            r"(?:doctor|medications|treatment|cure|solution)",
        ]

        points = []
        for pattern in pain_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                points.append(pattern)

        return points[:2] if points else []

    def _fingerprint(self, text: str) -> str:
        """Create fingerprint for deduplication."""
        import hashlib
        return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:16]
