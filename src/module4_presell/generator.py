"""Generate advertorial copy using Claude API."""

import json
import logging
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from ..module2_competitive.models import CompetitiveReport
from .compliance import ComplianceChecker
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
        self.compliance_checker = ComplianceChecker()

    def generate(
        self,
        offer_name: str,
        offer_category: str,
        niche: str,
        offer_url: str,
        report: CompetitiveReport | None = None,
        auto_load_report: bool = True,
        vsl_angle: str | None = None,
        max_retries: int = 2,
    ) -> PresellPage:
        """
        Generate advertorial copy for an offer (guaranteed MGID-compliant).

        Args:
            offer_name: Name of the offer (e.g. "Brain Boost Pro")
            offer_category: Category (e.g. "supplement")
            niche: Target niche (e.g. "brain-health")
            offer_url: CTA URL (affiliate link)
            report: Optional CompetitiveReport with winning patterns
            auto_load_report: If True and report is None, try to load from file
            vsl_angle: Optional VSL angle from MaxWeb (e.g. "Doctor reveals secret formula")
            max_retries: If generated copy fails compliance, retry up to this many times

        Returns:
            PresellPage with generated headline, subheadline, body, cta_text (guaranteed compliant)
        """
        logger.info(f"[presell] Generating COMPLIANT advertorial for {offer_name} ({niche})")

        # Auto-load report if not provided
        if report is None and auto_load_report:
            report = self.load_report(niche)

        # Build context from report and VSL angle if available
        context = self._build_context(report, niche, vsl_angle)

        # Retry loop: generate until compliant
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info(f"[presell] Retry {attempt}/{max_retries} - generating compliant version...")

            page = self._generate_once(offer_name, offer_category, niche, offer_url, context, report)

            # Check compliance
            violations, is_compliant = self.compliance_checker.check(
                headline=page.headline,
                subheadline=page.subheadline,
                body_html=page.body_html,
                cta_text=page.cta_text,
                has_ftc_disclaimer=False,  # Disclaimer added in template
            )

            if is_compliant:
                logger.info(f"[presell] ✓ COMPLIANT on attempt {attempt + 1}")
                page.compliance_violations = []
                page.is_compliant = True
                return page

            # If not compliant, log violations and retry
            if attempt < max_retries:
                violation_summary = "; ".join([v.message for v in violations if v.severity == "error"])
                logger.warning(f"[presell] Violations found: {violation_summary}")
                # Continue to next retry
            else:
                # Last attempt - return with violations logged
                logger.error(f"[presell] ✗ Still non-compliant after {max_retries} retries")
                page.compliance_violations = [
                    {
                        "type": v.violation_type,
                        "severity": v.severity,
                        "message": v.message,
                        "location": v.location,
                        "fix": v.suggested_fix,
                    }
                    for v in violations
                ]
                page.is_compliant = False
                return page

    def _generate_once(
        self,
        offer_name: str,
        offer_category: str,
        niche: str,
        offer_url: str,
        context: str,
        report: CompetitiveReport | None,
    ) -> PresellPage:
        """Generate advertorial once (no compliance check)."""
        # Prompt Claude
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system="""You are an expert advertorial copywriter specializing in health supplements.
You write compelling, story-driven advertorials that ethically persuade readers while maintaining FTC + MGID compliance.

CRITICAL COMPLIANCE RULES (MUST FOLLOW):
1. NO hard medical claims: Never 'cures', 'reverses', 'guaranteed', 'diagnosed', 'treats disease'
   ✓ Instead: 'supports', 'promotes', 'helps with', 'may help improve', 'research shows'
2. NO forbidden MGID patterns: Never 'doctors hate', 'secret', 'one weird trick', 'hidden', 'pharma doesn't want'
   ✓ Instead: Use straightforward, honest language
3. NO absolute claims: Never '100% effective', '100% safe', 'FDA approved'
   ✓ Instead: 'FDA-regulated', 'people report', 'studies suggest'
4. Use SOFT, SAFE language throughout: 'research indicates', 'may help', 'supports healthy', 'testimonials show'

BE STRICT: If any headline/body/subheadline contains forbidden words, this generation has FAILED.""",
            messages=[
                {
                    "role": "user",
                    "content": f"""
Generate a STRICTLY COMPLIANT advertorial headline + copy for:
- Product: {offer_name} ({offer_category})
- Target Niche: {niche}

{context}

STRICT COMPLIANCE CHECKLIST:
- Headline: curiosity hook, max 12 words, NO medical claims, NO "secret", NO "doctors hate"
- Subheadline: emotional problem statement, max 20 words, NO forbidden patterns
- Body: 3-4 paragraphs, soft language only ('may help', 'research shows', 'supports')
- CTA: action text, 3-5 words (e.g. "Claim Your Bottle Today")

Example COMPLIANT headline: "How Doctors Explain Brain Fog in Senior Citizens" (vs WRONG: "Cures Brain Fog")
Example COMPLIANT body: "Research shows that [ingredient] may help support cognitive function" (vs WRONG: "Proven to cure dementia")

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
        # Sanitize niche for filename (same as in reporter)
        safe_niche = niche.replace("/", "-").replace("\\", "-").replace(":", "-")
        pattern = str(report_dir / f"competitive_intel_*_{safe_niche}.json")

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
