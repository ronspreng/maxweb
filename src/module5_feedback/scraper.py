"""Scrape campaign data from ClickHub tracker via session."""

import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from .models import CampaignAnalysis, SubIdMetrics

logger = logging.getLogger(__name__)

load_dotenv()


class ClickHubScraper:
    """Scrape campaign metrics from ClickHub tracker."""

    def __init__(self):
        self.base_url = os.getenv("CLICKHUB_URL", "https://tracker.clickhub.co")
        self.email = os.getenv("CLICKHUB_EMAIL")
        self.password = os.getenv("CLICKHUB_PASSWORD")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def login(self) -> bool:
        """Login to ClickHub tracker."""
        try:
            # Attempt login
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url)

            if response.status_code == 200:
                # Parse login form and submit credentials
                soup = BeautifulSoup(response.content, "html.parser")

                # Find CSRF token if present
                csrf_token = None
                csrf_input = soup.find("input", {"name": "csrf"})
                if csrf_input:
                    csrf_token = csrf_input.get("value")

                # Submit login
                login_data = {
                    "email": self.email,
                    "password": self.password,
                }
                if csrf_token:
                    login_data["csrf"] = csrf_token

                response = self.session.post(login_url, data=login_data)

                logger.info("[clickhub] Login attempt completed")
                return response.status_code == 200
            return False

        except Exception as e:
            logger.error(f"[clickhub] Login failed: {e}")
            return False

    def fetch_campaigns(self) -> list[dict]:
        """Fetch list of campaigns."""
        try:
            url = f"{self.base_url}/campaigns"
            response = self.session.get(url)

            if response.status_code != 200:
                logger.error(f"[clickhub] Failed to fetch campaigns: {response.status_code}")
                return []

            soup = BeautifulSoup(response.content, "html.parser")
            campaigns = []

            # Parse campaign rows (adjust selector based on actual HTML)
            for row in soup.find_all("tr", {"class": re.compile("campaign|row")}):
                cells = row.find_all("td")
                if len(cells) >= 5:
                    campaign = {
                        "name": cells[0].text.strip(),
                        "clicks": int(self._parse_number(cells[1].text)),
                        "conversions": int(self._parse_number(cells[2].text)),
                        "revenue": float(self._parse_number(cells[3].text)),
                        "spend": float(self._parse_number(cells[4].text)),
                    }
                    campaigns.append(campaign)

            logger.info(f"[clickhub] Fetched {len(campaigns)} campaigns")
            return campaigns

        except Exception as e:
            logger.error(f"[clickhub] Error fetching campaigns: {e}")
            return []

    def fetch_campaign_details(self, campaign_id: str) -> list[SubIdMetrics]:
        """Fetch detailed metrics for a campaign (by Sub-ID)."""
        try:
            url = f"{self.base_url}/campaigns/{campaign_id}/details"
            response = self.session.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.content, "html.parser")
            sub_ids = []

            # Parse Sub-ID rows
            for row in soup.find_all("tr", {"class": re.compile("subid|detail|variant")}):
                cells = row.find_all("td")
                if len(cells) >= 6:
                    sub_id_str = cells[0].text.strip()

                    # Parse Sub-ID format: network_geo_device_daypart_ad_id_landing_id
                    parts = sub_id_str.split("_")
                    if len(parts) >= 6:
                        sub_id_metrics = SubIdMetrics(
                            sub_id=sub_id_str,
                            network=parts[0],
                            geo=parts[1],
                            device=parts[2],
                            daypart=parts[3],
                            ad_id=parts[4],
                            landing_id=parts[5],
                            clicks=int(self._parse_number(cells[1].text)),
                            conversions=int(self._parse_number(cells[2].text)),
                            revenue=float(self._parse_number(cells[3].text)),
                            spend=float(self._parse_number(cells[4].text)),
                        )
                        sub_ids.append(sub_id_metrics)

            logger.info(f"[clickhub] Fetched {len(sub_ids)} Sub-IDs for campaign {campaign_id}")
            return sub_ids

        except Exception as e:
            logger.error(f"[clickhub] Error fetching campaign details: {e}")
            return []

    @staticmethod
    def _parse_number(value: str) -> str:
        """Extract numeric value from string."""
        match = re.search(r"[\d,.]+", value)
        if match:
            return match.group(0).replace(",", "")
        return "0"

    def analyze_campaign(self, campaign_name: str, days: int = 7) -> CampaignAnalysis:
        """Analyze a complete campaign for the last N days."""
        try:
            campaigns = self.fetch_campaigns()
            campaign = next((c for c in campaigns if campaign_name.lower() in c["name"].lower()), None)

            if not campaign:
                logger.error(f"[clickhub] Campaign '{campaign_name}' not found")
                return None

            # Fetch detailed Sub-ID data
            # Note: This is simplified - actual campaign_id extraction depends on ClickHub HTML
            sub_ids = self.fetch_campaign_details(campaign_name)

            analysis = CampaignAnalysis(
                offer_name=campaign_name,
                offer_id=campaign_name,  # TODO: get real ID from ClickHub
                date_range=f"{(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}",
                total_clicks=campaign.get("clicks", 0),
                total_conversions=campaign.get("conversions", 0),
                total_revenue=campaign.get("revenue", 0.0),
                total_spend=campaign.get("spend", 0.0),
                sub_ids=sub_ids,
            )

            logger.info(f"[clickhub] Analyzed campaign: {campaign_name}")
            return analysis

        except Exception as e:
            logger.error(f"[clickhub] Analysis error: {e}")
            return None
