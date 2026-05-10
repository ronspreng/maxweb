"""Generate advertorial copy using Claude API."""

import json
import logging
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from ..module2_competitive.models import CompetitiveReport
from .models import PresellPage

# Load .env explicitly (same issue as analyzer.py)
_env_file = Path(__file__).parent.parent.parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

logger = logging.getLogger(__name__)


class AdvertorialGenerator:
    """Generate advertorial copy using Claude Haiku."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self.client = Anthropic(api_key=api_key)

    def generate(
        self,
        offer_name: str,
        offer_category: str,
        niche: str,
        offer_url: str,
        report: CompetitiveReport | None = None,
        auto_load_report: bool = True,
        vsl_angle: str | None = None,
    ) -> PresellPage:
        """
        Generate advertorial copy for an offer.

        Args:
            offer_name: Name of the offer (e.g. "Brain Boost Pro")
            offer_category: Category (e.g. "supplement")
            niche: Target niche (e.g. "brain-health")
            offer_url: CTA URL (affiliate link)
            report: Optional CompetitiveReport with winning patterns
            auto_load_report: If True and report is None, try to load from file
            vsl_angle: Optional VSL angle from MaxWeb (e.g. "Doctor reveals secret formula")

        Returns:
            PresellPage with generated headline, subheadline, body, cta_text
        """
        logger.info(f"[presell] Generating advertorial for {offer_name} ({niche})")

        # Auto-load report if not provided
        if report is None and auto_load_report:
            report = self.load_report(niche)

        # Build context from report and VSL angle if available
        context = self._build_context(report, niche, vsl_angle)

        # Prompt Claude
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system="You are an expert advertorial copywriter specializing in health supplements. You write compelling, story-driven advertorials that ethically persuade readers. Always include FTC compliance awareness. Respond with valid JSON only.",
            messages=[
                {
                    "role": "user",
                    "content": f"""
Write an advertorial for:
- Product: {offer_name} ({offer_category})
- Target Niche: {niche}

{context}

Instructions:
1. Headline: curiosity-gap hook, max 12 words, no ALL CAPS
2. Subheadline: problem agitation, max 20 words, emotional
3. Body: 3-4 paragraphs, HTML format (<p>...</p>), narrative style, 150-300 words total
   - Open with a relatable problem
   - Build credibility and authority
   - Introduce the solution (product name)
   - Share benefits and social proof
4. CTA text: action-oriented, 3-5 words (e.g. "Claim Your Bottle Today")

Output ONLY valid JSON (no markdown, no code blocks):
{{
  "headline": "...",
  "subheadline": "...",
  "body": "<p>...</p><p>...</p>",
  "cta_text": "..."
}}
""",
                }
            ],
        )

        # Parse response
        raw_output = response.content[0].text.strip()
        logger.debug(f"[presell] Claude response: {raw_output[:200]}...")

        # Strip markdown code blocks if present
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
            logger.error(f"[presell] Invalid JSON from Claude: {e}")
            logger.error(f"[presell] Raw: {cleaned[:500]}")
            raise ValueError(f"Claude returned invalid JSON: {e}")

        # Build PresellPage
        page = PresellPage(
            offer_name=offer_name,
            offer_url=offer_url,
            niche=niche,
            headline=data.get("headline", "")[:150],
            subheadline=data.get("subheadline", "")[:200],
            body_html=data.get("body", "")[:2000],
            cta_text=data.get("cta_text", "Get Started Today")[:50],
            source_report_niche=report.niche if report else None,
        )

        logger.info(f"[presell] Generated advertorial: {len(page.body_html)} chars")
        return page

    @staticmethod
    def load_report(niche: str) -> CompetitiveReport | None:
        """
        Load CompetitiveReport from JSON file.

        Args:
            niche: Niche to load report for

        Returns:
            CompetitiveReport or None if not found
        """
        import glob

        report_dir = Path("output/reports")
        pattern = str(report_dir / f"competitive_intel_*_{niche}.json")

        matches = glob.glob(pattern)
        if not matches:
            logger.warning(f"[presell] No report found for {niche} at {pattern}")
            return None

        # Get most recent
        latest_report = sorted(matches)[-1]
        logger.info(f"[presell] Loading report from {latest_report}")

        try:
            with open(latest_report) as f:
                data = json.load(f)

            # Reconstruct CompetitiveReport from JSON
            from ..module2_competitive.models import CreativePattern

            def make_pattern(p_dict, pattern_type):
                return CreativePattern(
                    pattern_type=pattern_type,
                    value=p_dict["value"],
                    frequency=p_dict.get("frequency", 1),
                    example_headlines=p_dict.get("example_headlines", []),
                    niche=data["niche"],
                )

            report = CompetitiveReport(
                niche=data["niche"],
                generated_at=data["generated_at"],
                ads_analyzed=data["ads_analyzed"],
                sources=data["sources"],
                top_hooks=[make_pattern(p, "hook") for p in data["top_hooks"]],
                top_emotional_triggers=[
                    make_pattern(p, "emotional_trigger")
                    for p in data["top_emotional_triggers"]
                ],
                top_image_archetypes=[
                    make_pattern(p, "image_archetype")
                    for p in data["top_image_archetypes"]
                ],
                top_power_words=[
                    make_pattern(p, "power_word") for p in data["top_power_words"]
                ],
                saturation_warnings=data.get("saturation_warnings", []),
                recommended_angles=data.get("recommended_angles", []),
                raw_claude_output="",
            )
            logger.info(f"[presell] Loaded report: {report.ads_analyzed} ads analyzed")
            return report

        except Exception as e:
            logger.error(f"[presell] Error loading report: {e}")
            return None

    def _build_context(self, report: CompetitiveReport | None, niche: str, vsl_angle: str | None = None) -> str:
        """Build context string from competitive report and VSL angle."""
        context_lines = []

        # Prioritize VSL angle if provided
        if vsl_angle:
            context_lines.extend([
                "CRITICAL: The MaxWeb VSL uses this main angle:",
                f"'{vsl_angle}'",
                "Your presell page MUST align with and support this angle.",
                "",
            ])

        if not report:
            msg = "No competitive report available. Use general best practices for this niche."
            if vsl_angle:
                msg += f" Focus on supporting the VSL angle: {vsl_angle}"
            context_lines.append(msg)
            return "\n".join(context_lines)

        context_lines.extend([
            "Winning patterns from competitive analysis:",
            "",
            "Top hooks (use to support the VSL angle):",
        ])

        for hook in report.top_hooks[:3]:
            context_lines.append(f"- {hook.value} (seen ~{hook.frequency}x)")

        context_lines.append("")
        context_lines.append("Emotional triggers that resonate:")
        for trigger in report.top_emotional_triggers[:3]:
            context_lines.append(f"- {trigger.value}")

        context_lines.append("")
        context_lines.append("High-impact power words:")
        words = ", ".join(p.value for p in report.top_power_words[:5])
        context_lines.append(f"- {words}")

        context_lines.append("")
        context_lines.append("Fresh angles to consider:")
        for angle in report.recommended_angles[:3]:
            context_lines.append(f"- {angle}")

        if report.saturation_warnings:
            context_lines.append("")
            context_lines.append("Patterns to avoid (oversaturated):")
            for warning in report.saturation_warnings[:3]:
                context_lines.append(f"- {warning}")

        return "\n".join(context_lines)
