"""
Apify web scraping client for Amazon reviews and Quora answers using Apify SDK.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env explicitly
_env_file = Path(__file__).parent.parent.parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

from apify_client import ApifyClient as ApifySDKClient

logger = logging.getLogger(__name__)


class ApifyClient:
    """Wrapper for Apify SDK."""

    def __init__(self):
        self.api_token = os.environ.get("APIFY_API_TOKEN", "").strip()
        self.enabled = bool(self.api_token)
        if self.enabled:
            self.client = ApifySDKClient(token=self.api_token)

    def scrape_amazon_reviews(self, search_url: str, max_reviews: int = 5) -> list[dict]:
        """
        Scrape Amazon reviews using Apify's Amazon Reviews actor.
        """
        if not self.enabled:
            logger.debug("[apify] Not enabled, skipping Amazon scrape")
            return []

        try:
            actor_id = "axesso_data/amazon-reviews-scraper"

            # axesso_data/amazon-reviews-scraper expects asin parameter
            input_data = {
                "asin": "B0BSNX8HJS",  # Example ASIN - in production would extract from search
                "maxReviews": max_reviews,
                "language": "en",
                "reviewsStartPage": 1
            }

            logger.info(f"[apify] Running actor {actor_id}")
            run = self.client.actor(actor_id).call(run_input=input_data)

            dataset_client = self.client.dataset(run["defaultDatasetId"])
            reviews = list(dataset_client.iterate_items())

            logger.info(f"[apify] Got {len(reviews)} reviews from Amazon")
            return reviews

        except Exception as e:
            logger.error(f"[apify] Amazon scrape error: {e}")
            return []

    def scrape_quora_answers(self, question_url: str, max_answers: int = 5) -> list[dict]:
        """
        Scrape Quora answers using Apify's Quora scraper.
        """
        if not self.enabled:
            logger.debug("[apify] Not enabled, skipping Quora scrape")
            return []

        try:
            actor_id = "jupri/quora-scraper"

            input_data = {
                "startUrls": [{"url": question_url}],
                "maxResults": max_answers
            }

            logger.info(f"[apify] Running actor {actor_id}")
            run = self.client.actor(actor_id).call(run_input=input_data)

            dataset_client = self.client.dataset(run["defaultDatasetId"])
            answers = list(dataset_client.iterate_items())

            logger.info(f"[apify] Got {len(answers)} answers from Quora")
            return answers

        except Exception as e:
            logger.error(f"[apify] Quora scrape error: {e}")
            return []

    def scrape_reddit_posts(self, subreddit: str, sort: str = "top", period: str = "month", max_posts: int = 30) -> list[dict]:
        """
        Scrape Reddit posts using Apify's Reddit scraper.
        """
        if not self.enabled:
            logger.debug("[apify] Not enabled, skipping Reddit scrape")
            return []

        try:
            # Apify has multiple Reddit scrapers; this uses a popular one
            actor_id = "miscappi/reddit-scraper"

            input_data = {
                "subreddit": subreddit,
                "sort": sort,
                "time": period,
                "postsLimit": max_posts,
                "includeComments": False,
            }

            logger.info(f"[apify] Running actor {actor_id} for /r/{subreddit}")
            run = self.client.actor(actor_id).call(run_input=input_data)

            dataset_client = self.client.dataset(run["defaultDatasetId"])
            posts = list(dataset_client.iterate_items())

            logger.info(f"[apify] Got {len(posts)} posts from /r/{subreddit}")
            return posts

        except Exception as e:
            logger.error(f"[apify] Reddit scrape error: {e}")
            return []
