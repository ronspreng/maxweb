"""Generate native ad creative variations using Claude API."""

import json
import logging
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from ..module4_presell.generator import AdvertorialGenerator
from .models import CreativeSet, NativeAdCreative

# Load .env explicitly
_env_file = Path(__file__).parent.parent.parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

logger = logging.getLogger(__name__)


class CreativeGenerator:
    """Generate native ad creative variations using Claude Haiku."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self.client = Anthropic(api_key=api_key)

    def generate(
        self,
        offer_name: str,
        niche: str,
        auto_load_report: bool = True,
    ) -> CreativeSet:
        """
        Generate multiple creative variations for an offer.

        Args:
            offer_name: Name of the offer (e.g. "Brain Boost Pro")
            niche: Target niche (e.g. "brain-health")
            auto_load_report: If True, try to load Module 2 report for patterns

        Returns:
            CreativeSet with 8 headline + description pairs
        """
        logger.info(f"[creative] Generating creatives for {offer_name} ({niche})")

        # Try to load Module 2 report for context
        report = None
        report_used = False
        if auto_load_report:
            report = AdvertorialGenerator.load_report(niche)
            if report:
                report_used = True
                logger.info(f"[creative] Using Module 2 patterns ({len(report.top_hooks)} hooks)")
            else:
                logger.info(f"[creative] No report found, using generic approach")

        # Build context
        context = self._build_context(report, niche)

        # Prompt Claude for creatives
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system="You are an expert native ad copywriter. Create compelling headlines and descriptions for MGID/Taboola native ads. Keep headlines max 60 chars, descriptions max 150 chars. Respond with valid JSON only.",
            messages=[
                {
                    "role": "user",
                    "content": f"""
Generate 8 native ad creative variations for {offer_name} ({niche}).
Create 2 variations for each hook type below.

Hook types and examples:
- curiosity: "This One Trick...", "Doctors Hate This Simple Trick..."
- fear: "Brain Fog? Read This Before...", "Warning: Your Supplements May Not..."
- authority: "Doctor Reveals...", "Scientists Discovered..."
- social_proof: "Millions Are Switching To...", "Join 500K Who Already..."

{context}

Important constraints:
- Headline: max 60 characters
- Description: max 150 characters
- Each description should be 2-3 sentences

Output ONLY valid JSON (no markdown, no code blocks):
{{
  "creatives": [
    {{"headline": "...", "description": "...", "hook_type": "curiosity"}},
    {{"headline": "...", "description": "...", "hook_type": "curiosity"}},
    {{"headline": "...", "description": "...", "hook_type": "fear"}},
    {{"headline": "...", "description": "...", "hook_type": "fear"}},
    {{"headline": "...", "description": "...", "hook_type": "authority"}},
    {{"headline": "...", "description": "...", "hook_type": "authority"}},
    {{"headline": "...", "description": "...", "hook_type": "social_proof"}},
    {{"headline": "...", "description": "...", "hook_type": "social_proof"}}
  ]
}}
""",
                }
            ],
        )

        # Parse response
        raw_output = response.content[0].text.strip()
        logger.debug(f"[creative] Claude response: {raw_output[:200]}...")

        # Strip markdown code blocks
        cleaned = raw_output
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```", 2)[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"[creative] Invalid JSON from Claude: {e}")
            logger.error(f"[creative] Raw: {cleaned[:500]}")
            raise ValueError(f"Claude returned invalid JSON: {e}")

        # Build CreativeSet
        creatives = []
        for c_dict in data.get("creatives", []):
            try:
                creative = NativeAdCreative(
                    headline=c_dict.get("headline", "")[:60],
                    description=c_dict.get("description", "")[:150],
                    hook_type=c_dict.get("hook_type", "story"),
                )
                creatives.append(creative)
            except Exception as e:
                logger.debug(f"[creative] Parse error: {e}")

        creative_set = CreativeSet(
            offer_name=offer_name,
            niche=niche,
            creatives=creatives,
            report_used=report_used,
        )

        logger.info(f"[creative] Generated {len(creative_set.creatives)} creatives")
        return creative_set

    def _build_context(self, report, niche: str) -> str:
        """Build context string from competitive report."""
        if not report:
            return "No competitive patterns available. Use general best practices for health/supplement niches."

        context_lines = [
            "Winning patterns from Module 2 analysis:",
            "",
            "Top hooks (use these themes):",
        ]

        for hook in report.top_hooks[:3]:
            context_lines.append(f"- {hook.value}")

        context_lines.append("")
        context_lines.append("Top emotional triggers:")
        for trigger in report.top_emotional_triggers[:3]:
            context_lines.append(f"- {trigger.value}")

        context_lines.append("")
        context_lines.append("Power words to use:")
        words = ", ".join(p.value for p in report.top_power_words[:5])
        context_lines.append(f"- {words}")

        context_lines.append("")
        context_lines.append("Fresh angles to explore:")
        for angle in report.recommended_angles[:2]:
            context_lines.append(f"- {angle}")

        return "\n".join(context_lines)
