"""
Reddit health niches scraper using Apify for reliable access.
"""

import hashlib
import logging
import re
from typing import Optional

from ..models import NativeAd
from .apify_client import ApifyClient

logger = logging.getLogger(__name__)

NICHE_SUBREDDITS = {
    "brain-health": ["Nootropics", "Cognition", "Productivity", "BrainFog"],
    "lung-health": ["Asthma", "Breathing", "Pulmonary", "RespiratoryHealth"],
    "mens-health": ["MentalHealth", "FitnessandNutrition", "Testosterone", "MenHealth"],
}

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

GENERIC_SUBREDDITS = ["Health", "HealthAdvice", "Medicine", "AskDocs"]


class RedditScraper:
    """Scrape Reddit posts for health pain points and winning language using Apify."""

    def __init__(self, niche: str, keywords: list[str] | None = None):
        self.niche = niche
        self.apify = ApifyClient()

        if niche in NICHE_SUBREDDITS:
            self.subreddits = NICHE_SUBREDDITS[niche]
        else:
            subreddits_set = set()
            if keywords:
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in KEYWORD_SUBREDDITS:
                        subreddits_set.update(KEYWORD_SUBREDDITS[keyword_lower])

            if subreddits_set:
                self.subreddits = list(subreddits_set)[:6]
            else:
                self.subreddits = GENERIC_SUBREDDITS

    def scrape(self) -> list[NativeAd]:
        """Scrape Reddit posts — currently disabled."""
        logger.warning(
            "[reddit] Reddit scraper is disabled. Options:\n"
            "1. Apify: No public Reddit scrapers available as of May 2026\n"
            "2. Direct access: Reddit blocks all automated requests (API, RSS, browser)\n"
            "3. Alternative: Use DailyMail scraper (working) or other sources"
        )
        return []

    def _extract_pain_points(self, text: str) -> list[str]:
        """Extract pain points and triggers from text."""
        pain_patterns = [
            r"(?:struggling|suffering|dealing with|problem with|issue with|can't|unable to|difficulty)",
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
        return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:16]
