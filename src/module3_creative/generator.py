"""Generate native ad creatives using Claude Haiku."""
import json
import logging
import os
from pathlib import Path

from anthropic import Anthropic

from .models import CreativeSet, NativeAdCreative

logger = logging.getLogger(__name__)


class CreativeGenerator:
    """Generate native ad headlines + descriptions for MGID/Taboola."""

    def __init__(self):
        self.client = Anthropic()
        self.model = "claude-3-5-haiku-20241022"

    def generate(
        self,
        offer_name: str,
        niche: str,
        report: dict | None = None,
        auto_load: bool = True,
    ) -> CreativeSet:
        """Generate 8 native ad creatives.

        Args:
            offer_name: Name of the offer (e.g., "Gluco Savior")
            niche: Target niche (e.g., "health")
            report: Optional Module 2 competitive report (dict)
            auto_load: Try auto-load report from /output/ if not provided

        Returns:
            CreativeSet with 8-10 creatives
        """
        # Try load report if not provided
        if report is None and auto_load:
            report = self._load_report(offer_name)

        # Build prompt
        prompt = self._build_prompt(offer_name, niche, report)

        # Call Claude Haiku
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        response_text = message.content[0].text
        creatives = self._parse_response(response_text)

        return CreativeSet(
            offer_name=offer_name,
            niche=niche,
            creatives=creatives,
            report_used=(report is not None),
        )

    def _load_report(self, offer_name: str) -> dict | None:
        """Load Module 2 report from /output/."""
        output_dir = Path("output") / "reports"
        if not output_dir.exists():
            return None

        # Look for report file matching offer name
        for report_file in output_dir.glob("*.json"):
            try:
                with open(report_file) as f:
                    data = json.load(f)
                    if data.get("offer") == offer_name:
                        logger.info(f"Loaded report: {report_file}")
                        return data
            except (json.JSONDecodeError, IOError):
                continue

        return None

    def _build_prompt(self, offer_name: str, niche: str, report: dict | None) -> str:
        """Build prompt for Claude."""
        base = f"""Generate 8 native ad creatives for MGID/Taboola.

Offer: {offer_name}
Niche: {niche}

Requirements:
- Headline: max 60 chars
- Description: max 150 chars
- 2 per hook type: curiosity, fear, authority, social_proof, story
- Hook types create psychological engagement angles
- Native ads mimic editorial/social content

Output format (JSON):
{{"creatives": [{{"headline": "...", "description": "...", "hook_type": "..."}}]}}
"""

        if report:
            patterns = report.get("winning_patterns", [])
            if patterns:
                base += f"\nWinning patterns from competitors:\n"
                for p in patterns[:3]:
                    base += f"- {p}\n"

        return base

    def _parse_response(self, response_text: str) -> list[NativeAdCreative]:
        """Parse JSON from Claude response."""
        # Strip markdown code blocks if present
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.rstrip("`")

        data = json.loads(response_text.strip())
        creatives = []

        for item in data.get("creatives", []):
            try:
                creative = NativeAdCreative(
                    headline=item["headline"],
                    description=item["description"],
                    hook_type=item["hook_type"],
                )
                creatives.append(creative)
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipped invalid creative: {e}")

        return creatives
