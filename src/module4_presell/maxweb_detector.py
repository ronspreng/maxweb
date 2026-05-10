"""Detect VSL angle from MaxWeb offer pages."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import requests
from anthropic import Anthropic
from dotenv import load_dotenv

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

    def detect(self, maxweb_url: str) -> Optional[dict]:
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
