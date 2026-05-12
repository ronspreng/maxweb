"""Detect VSL angle from MaxWeb offer pages."""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests
from anthropic import Anthropic
from bs4 import BeautifulSoup
from dotenv import load_dotenv

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

_env_file = Path(__file__).parent.parent.parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

logger = logging.getLogger(__name__)


class MaxWebDetector:
    """Extract VSL angle/hook from MaxWeb offer pages."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self.client = Anthropic(api_key=api_key)
        self.maxweb_email = os.environ.get("MAXWEB_EMAIL", "")
        self.maxweb_password = os.environ.get("MAXWEB_PASSWORD", "")

    def detect(self, offer_name: str) -> Optional[dict]:
        """
        Detect VSL angle from MaxWeb offer.

        Args:
            offer_name: Name of the offer (e.g. "Brain Memory Keeper")

        Returns:
            Dict with VSL angle details, or None if not found
        """
        # Try to find the MaxWeb URL first
        maxweb_url = self.find_maxweb_url(offer_name)

        if not maxweb_url:
            logger.warning(f"[maxweb] Could not find URL for {offer_name}")
            return None

        return self._detect_from_url(maxweb_url)

    def find_maxweb_url(self, offer_name: str) -> Optional[str]:
        """Find MaxWeb offer URL by name."""
        logger.info(f"[maxweb] Searching for: {offer_name}")

        # Strategy 1: Try direct URL pattern
        slug = self._slugify(offer_name)
        direct_url = f"https://maxweb.com/offer/{slug}"

        if self._url_exists(direct_url):
            logger.info(f"[maxweb] Found via direct pattern: {direct_url}")
            return direct_url

        # Strategy 2: Playwright scraping of MaxWeb search
        if HAS_PLAYWRIGHT:
            try:
                url = self._search_maxweb_playwright(offer_name)
                if url:
                    logger.info(f"[maxweb] Found via Playwright: {url}")
                    return url
            except Exception as e:
                logger.warning(f"[maxweb] Playwright search failed: {e}")

        # Strategy 3: Google search
        try:
            url = self._search_google(offer_name)
            if url:
                logger.info(f"[maxweb] Found via Google: {url}")
                return url
        except Exception as e:
            logger.warning(f"[maxweb] Google search failed: {e}")

        return None

    def _slugify(self, text: str) -> str:
        """Convert text to URL slug."""
        return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

    def _url_exists(self, url: str) -> bool:
        """Check if URL is accessible."""
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            return response.status_code < 400
        except:
            return False

    def _search_maxweb_playwright(self, offer_name: str) -> Optional[str]:
        """Use Playwright to find offer on MaxWeb."""
        if not HAS_PLAYWRIGHT:
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://maxweb.com/offers")
                time.sleep(2)

                # Search for offer
                page.fill("input[placeholder*='search' i]", offer_name)
                page.press("input", "Enter")
                time.sleep(2)

                # Get first result link
                links = page.query_selector_all("a[href*='/offer/']")
                if links:
                    href = links[0].get_attribute("href")
                    browser.close()
                    if href.startswith("/"):
                        return f"https://maxweb.com{href}"
                    return href

                browser.close()
        except Exception as e:
            logger.debug(f"[maxweb] Playwright error: {e}")

        return None

    def _search_google(self, offer_name: str) -> Optional[str]:
        """Search Google for MaxWeb offer link."""
        try:
            query = f'"{offer_name}" site:maxweb.com/offer'
            url = f"https://www.google.com/search?q={quote(query)}"

            response = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

            soup = BeautifulSoup(response.text, "html.parser")
            for link in soup.find_all("a"):
                href = link.get("href", "")
                if "maxweb.com/offer/" in href:
                    # Extract clean URL from Google redirect
                    if "/url?q=" in href:
                        href = href.split("/url?q=")[1].split("&")[0]
                    return href

        except Exception as e:
            logger.debug(f"[maxweb] Google search error: {e}")

        return None

    def _detect_from_url(self, maxweb_url: str) -> Optional[dict]:
        """
        Detect VSL angle from MaxWeb offer page.

        Args:
            maxweb_url: URL to MaxWeb offer (e.g. https://maxweb.com/offer/brain-boost-pro)

        Returns:
            Dict with 'angle', 'hook_type', 'main_claim', 'emotional_trigger', or None if failed
        """
        logger.info(f"[maxweb] Detecting VSL angle from {maxweb_url}")

        try:
            # Fetch the page
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(maxweb_url, headers=headers, timeout=10)
            response.raise_for_status()

            content = response.text

            # Extract text content (remove scripts, styles)
            content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
            content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL)
            content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\s+", " ", content).strip()

            if not content:
                logger.warning(f"[maxweb] No content extracted from {maxweb_url}")
                return None

            # Take first 3000 chars for analysis
            content_snippet = content[:3000]
            logger.debug(f"[maxweb] Extracted {len(content_snippet)} chars")

            # Use Claude to detect angle
            return self._analyze_with_claude(content_snippet, maxweb_url)

        except Exception as e:
            logger.error(f"[maxweb] Detection failed: {e}")
            return None

    def _analyze_with_claude(self, content: str, url: str) -> Optional[dict]:
        """Use Claude to extract VSL angle from page content."""
        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                system="You are an expert copywriter analyzing VSL (video sales letter) offers. Extract the main angle/hook in JSON format only.",
                messages=[
                    {
                        "role": "user",
                        "content": f"""Analyze this MaxWeb VSL and extract the core angle/hook/promise.

Content snippet:
{content}

Respond with ONLY valid JSON (no markdown):
{{
  "angle": "Brief main angle (e.g. 'Doctor reveals secret brain formula')",
  "hook_type": "One of: curiosity, fear, authority, social_proof, story, benefit",
  "main_claim": "The core promise (e.g. '30-day brain fog reversal')",
  "emotional_trigger": "What emotion it targets (e.g. 'health anxiety', 'missed opportunity')"
}}""",
                    }
                ],
            )

            raw_output = response.content[0].text.strip()
            logger.debug(f"[maxweb] Claude response: {raw_output[:200]}")

            # Parse JSON
            cleaned = raw_output
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```", 2)[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)

            result = {
                "angle": data.get("angle", ""),
                "hook_type": data.get("hook_type", "story"),
                "main_claim": data.get("main_claim", ""),
                "emotional_trigger": data.get("emotional_trigger", ""),
                "source_url": url,
            }

            logger.info(
                f"[maxweb] Detected: {result['angle']} ({result['hook_type']} hook)"
            )
            return result

        except Exception as e:
            logger.error(f"[maxweb] Analysis failed: {e}")
            return None
