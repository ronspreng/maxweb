"""
Claude API pattern analyzer for native ad competitive intelligence.
"""

import json
import logging
import os

import anthropic
from dotenv import load_dotenv

from .models import CompetitiveReport, CreativePattern, NativeAd

load_dotenv()
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert direct response media buyer analyzing native ad
creatives for US health/nutra advertisers. Your audience is 55-72 year old Americans
on news sites (Daily Mail, MSN, Yahoo, Fox News). You think like a winning affiliate:
you spot what patterns are being scaled (= working), what's saturated (= avoid), and
what gaps exist (= opportunity).

Always output strict JSON matching the schema provided. No markdown, no explanation
outside the JSON structure. All string values in English."""

_ANALYSIS_PROMPT_TEMPLATE = """Analyze these {count} native ad headlines from the
US {niche_label} niche. These are real ads running right now.

ADS:
{ads_block}

Return ONLY this JSON structure — no other text:
{{
  "top_hooks": [
    {{"value": "string", "frequency": int, "example_headlines": ["str", "str"]}}
  ],
  "top_emotional_triggers": [
    {{"value": "string", "frequency": int, "example_headlines": ["str"]}}
  ],
  "top_image_archetypes": [
    {{"value": "string", "frequency": int, "example_headlines": []}}
  ],
  "top_power_words": [
    {{"value": "string", "frequency": int, "example_headlines": []}}
  ],
  "saturation_warnings": ["pattern that appears 5+ times and is likely saturated"],
  "recommended_angles": [
    "Fresh angle 1 that is NOT yet saturated in these ads",
    "Fresh angle 2 ...",
    "Fresh angle 3 ..."
  ]
}}

Rules:
- top_hooks: exactly 5 items (a "hook" is a narrative opener like "doctor reveals", "this one weird trick", "dermatologists hate")
- top_emotional_triggers: exactly 5 items (fear of decline, curiosity gap, social proof, urgency, etc.)
- top_image_archetypes: exactly 5 items (infer from headline context — e.g. "before/after" if weight-loss phrasing, "doctor in white coat" if authority angle)
- top_power_words: exactly 10 items (single words only, no phrases — extract the most common high-impact words)
- saturation_warnings: any pattern that appears 5+ times in your analysis
- recommended_angles: exactly 3 fresh angles specific to {niche_label} that do NOT already appear in the ads above
- frequency = estimated count across the ads provided

All string values must be in English."""


NICHE_LABELS = {
    "brain-health": "brain health / memory",
    "lung-health": "lung health / respiratory",
    "mens-health": "men's health / vitality",
}


class PatternAnalyzer:
    """Sends scraped ads to Claude API and extracts creative patterns."""

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "NOT_SET")
        logger.info(f"API Key loaded: {key[:20]}... (len={len(key)})")
        self.client = anthropic.Anthropic(api_key=key)

    def analyze(self, ads: list[NativeAd], niche: str) -> CompetitiveReport:
        """
        Analyze a batch of native ads and return a CompetitiveReport.

        Sends up to 80 ads to Claude; if more, takes a representative sample.
        """
        sample = ads[:80]
        niche_label = NICHE_LABELS.get(niche, niche.replace("-", " "))

        ads_block = "\n".join(f"{i+1}. {ad.headline}" for i, ad in enumerate(sample))

        prompt = _ANALYSIS_PROMPT_TEMPLATE.format(
            count=len(sample),
            niche_label=niche_label,
            ads_block=ads_block,
        )

        logger.info(f"Sending {len(sample)} ads to Claude for {niche} analysis")

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        raw_output = response.content[0].text
        logger.debug(f"Claude raw output: {raw_output[:200]}...")

        return self._parse_response(raw_output, ads, niche, sample)

    def _parse_response(
        self,
        raw: str,
        all_ads: list[NativeAd],
        niche: str,
        sample: list[NativeAd],
    ) -> CompetitiveReport:
        """Parse Claude JSON response into CompetitiveReport."""
        try:
            # Strip markdown code blocks if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                # Remove ```json or ``` prefix
                cleaned = cleaned.split("```", 2)[1]
                # Remove json language identifier if present
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                # Remove trailing ```
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Claude returned invalid JSON: {e}\nRaw: {raw[:500]}")
            return CompetitiveReport(
                niche=niche,
                ads_analyzed=len(sample),
                sources=list({ad.source_site for ad in sample}),
                raw_claude_output=raw,
            )

        def to_patterns(items: list, ptype: str) -> list[CreativePattern]:
            return [
                CreativePattern(
                    pattern_type=ptype,  # type: ignore[arg-type]
                    value=item.get("value", ""),
                    frequency=max(1, item.get("frequency", 1)),  # Ensure frequency >= 1
                    example_headlines=item.get("example_headlines", []),
                    niche=niche,
                )
                for item in items
                if item.get("value") and item.get("frequency", 1) > 0
            ]

        return CompetitiveReport(
            niche=niche,
            ads_analyzed=len(sample),
            sources=list({ad.source_site for ad in all_ads}),
            top_hooks=to_patterns(data.get("top_hooks", []), "hook"),
            top_emotional_triggers=to_patterns(
                data.get("top_emotional_triggers", []), "emotional_trigger"
            ),
            top_image_archetypes=to_patterns(
                data.get("top_image_archetypes", []), "image_archetype"
            ),
            top_power_words=to_patterns(data.get("top_power_words", []), "power_word"),
            saturation_warnings=data.get("saturation_warnings", []),
            recommended_angles=data.get("recommended_angles", []),
            raw_claude_output=raw,
        )
