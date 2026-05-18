"""
Quora Q&A scraper using requests instead of Playwright to bypass anti-bot detection.
"""

import hashlib
import logging
import random
import re
import time

import requests
from bs4 import BeautifulSoup

from ..models import NativeAd

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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


class QuoraAnswerScraper:
    """Scrape Quora questions as winning language patterns."""

    def __init__(self, niche: str):
        self.niche = niche
        self.questions = QUORA_QUESTIONS.get(niche, [])

    def scrape(self) -> list[NativeAd]:
        """Scrape Quora questions and answers."""
        logger.warning(
            "[quora] Quora scraper is currently disabled due to active anti-scraping measures. "
            "Quora blocks all automated requests (HTTP 403 Forbidden). "
            "Consider using alternative data sources for competitive intelligence."
        )
        return []

    def _scrape_question(self, question_slug: str) -> list[NativeAd]:
        """Scrape answers for a specific Quora question."""
        answers = []

        url = f"https://www.quora.com/{question_slug}"
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract question title and answers
            # Look for span with question text
            question_spans = soup.find_all("span")

            # Extract answer sections
            answer_sections = soup.find_all("div", class_=re.compile(r"(Answer|answer)", re.I))

            if not answer_sections:
                logger.debug(f"[quora] No answer divs found for {question_slug}")
                # Fallback: look for any div with substantial text
                all_divs = soup.find_all("div")
                answer_sections = [d for d in all_divs if len(d.get_text(strip=True)) > 100][:10]

            for section in answer_sections[:4]:
                try:
                    text = section.get_text(strip=True)

                    # Filter by length
                    if not text or len(text) < 20 or len(text) > 1000:
                        continue

                    # First line as headline
                    headline = text.split("\n")[0][:150].strip()

                    if len(headline) < 15:
                        continue

                    ad = NativeAd(
                        headline=headline,
                        landing_url=url,
                        source_site="quora",
                        niche=self.niche,
                        ad_network="quora",
                        fingerprint=self._fingerprint(headline),
                    )

                    # Avoid duplicates
                    if not any(a.fingerprint == ad.fingerprint for a in answers):
                        answers.append(ad)

                except Exception as e:
                    logger.debug(f"[quora] Parse error: {e}")

        except Exception as e:
            logger.warning(f"[quora] Failed to scrape {url}: {e}")

        return answers

    @staticmethod
    def _fingerprint(text: str) -> str:
        """Create fingerprint for deduplication."""
        return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:16]
