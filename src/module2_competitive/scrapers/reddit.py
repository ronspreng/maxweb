"""
Reddit health niches scraper for pain points and winning language patterns.
"""

import json
import logging
import re
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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


class RedditScraper:
    """Scrape Reddit posts for health pain points and winning language."""

    def __init__(self, niche: str):
        self.niche = niche
        self.subreddits = NICHE_SUBREDDITS.get(niche, [])

    def scrape(self) -> list[NativeAd]:
        """Scrape Reddit posts and convert to NativeAd objects."""
        all_ads = []

        for subreddit in self.subreddits:
            logger.info(f"[reddit] Scraping /r/{subreddit}")
            posts = self._scrape_subreddit(subreddit)
            all_ads.extend(posts)

        logger.info(f"[reddit] Total posts collected: {len(all_ads)}")
        return all_ads[:50]  # Top 50 posts

    def _scrape_subreddit(self, subreddit: str) -> list[NativeAd]:
        """Scrape a single subreddit for top posts."""
        ads = []

        try:
            # Use pushshift/Reddit API to get posts
            url = f"https://www.reddit.com/r/{subreddit}/top.json?t=month&limit=30"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(url, headers=headers, timeout=10)
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
