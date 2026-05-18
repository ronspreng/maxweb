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
        """Scrape a single subreddit for top posts."""
        ads = []
        import random

        try:
            # Use Reddit API with better headers
            url = f"https://www.reddit.com/r/{subreddit}/top.json?t=month&limit=30"
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            response = requests.get(url, headers=headers, timeout=15)

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning(f"[reddit] Rate limited on /r/{subreddit}, waiting...")
                time.sleep(5)
                return []

            if response.status_code == 500:
                logger.warning(f"[reddit] Server error on /r/{subreddit}, skipping...")
                return []

            response.raise_for_status()
            data = response.json()

            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})

                title = post_data.get("title", "").strip()
                score = post_data.get("score", 0)
                num_comments = post_data.get("num_comments", 0)

                if not title or len(title) < 10:
                    continue

                # Extract pain points from title
                pain_points = self._extract_pain_points(title)
                if not pain_points:
                    continue

                post_url = f"https://reddit.com{post_data.get('permalink', '')}"

                ads.append(
                    NativeAd(
                        headline=title,
                        landing_url=post_url,
                        source_site="reddit",
                        niche=self.niche,
                        ad_network="reddit",
                        fingerprint=self._fingerprint(title),
                        metadata={
                            "score": score,
                            "comments": num_comments,
                            "subreddit": subreddit,
                            "pain_points": pain_points,
                        },
                    )
                )

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
