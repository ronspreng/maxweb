"""Generate native ad creatives using Claude Haiku."""
import json
import logging
import os
from pathlib import Path

from anthropic import Anthropic

from ..module4_presell.compliance import ComplianceChecker
from .models import CreativeSet, NativeAdCreative

logger = logging.getLogger(__name__)


# Niche -> typische doelgroep voor image-generatie
NICHE_DEMOGRAPHICS = {
    "brain-health":  {"age": "55-70 years old", "skin_tone": "varied", "gender": "60% female", "hair": "silver/grey", "context": "home environment, daily life, family interactions"},
    "lung-health":   {"age": "50-70 years old", "skin_tone": "varied", "gender": "mixed",        "hair": "greying", "context": "outdoor activity struggle, breathing, stair-climbing"},
    "mens-health":   {"age": "45-65 years old", "skin_tone": "varied", "gender": "male",         "hair": "salt-and-pepper", "context": "athletic/active middle-aged man, gym, work"},
    "weight-loss":   {"age": "35-55 years old", "skin_tone": "varied", "gender": "70% female", "hair": "any",      "context": "before/after, kitchen, mirror moments"},
    "joint-health":  {"age": "55-75 years old", "skin_tone": "varied", "gender": "60% female", "hair": "grey",     "context": "stairs, gardening, picking up grandchild, knee/hip discomfort"},
    "diabetes":      {"age": "50-70 years old", "skin_tone": "varied", "gender": "mixed",        "hair": "any",      "context": "kitchen, glucose monitor, healthy food"},
    "general":       {"age": "45-65 years old", "skin_tone": "varied", "gender": "mixed",        "hair": "any",      "context": "everyday life, relatable health concern"},
}


def _demographics_for_niche(niche: str) -> dict:
    """Lookup demographics with sensible fallback."""
    if not niche:
        return NICHE_DEMOGRAPHICS["general"]
    key = niche.lower().strip()
    return NICHE_DEMOGRAPHICS.get(key, NICHE_DEMOGRAPHICS["general"])




class CreativeGenerator:
    """Generate native ad headlines + descriptions for MGID/Taboola."""

    def __init__(self):
        self.client = Anthropic()
        self.model = "claude-haiku-4-5-20251001"
        self.compliance_checker = ComplianceChecker()

    def generate(
        self,
        offer_name: str,
        niche: str,
        report: dict | None = None,
        auto_load: bool = True,
        max_retries: int = 2,
        vsl_hook: str | None = None,
        vsl_main_claim: str | None = None,
        vsl_emotional_trigger: str | None = None,
    ) -> CreativeSet:
        """Generate 8 MGID-compliant native ad creatives.

        Args:
            offer_name: Name of the offer (e.g., "Gluco Savior")
            niche: Target niche (e.g., "health")
            report: Optional Module 2 competitive report (dict)
            auto_load: Try auto-load report from /output/ if not provided
            max_retries: If creatives fail compliance, retry up to this many times
            vsl_hook: Primary VSL hook_type (e.g. "fear", "curiosity") — weights creative
                distribution: 50% match VSL hook, 50% spread over others. If None: equal split.
            vsl_main_claim: Core VSL promise (e.g. "Restore sharp focus"). Used in image-prompts
                to align visuals with the offer's specific value-proposition.
            vsl_emotional_trigger: Emotion the VSL targets (e.g. "health anxiety + FOMO"). Used
                to tune the emotional tone of generated image-prompts.

        Returns:
            CreativeSet with 8 compliant creatives
        """
        # Try load report if not provided
        if report is None and auto_load:
            report = self._load_report(offer_name)

        # Retry loop: generate until all creatives are compliant
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info(f"[creative] Retry {attempt}/{max_retries} - generating compliant headlines...")

            # Build prompt
            prompt = self._build_prompt(offer_name, niche, report, vsl_hook=vsl_hook, vsl_main_claim=vsl_main_claim, vsl_emotional_trigger=vsl_emotional_trigger)

            # Call Claude
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                system="""You are an expert native ad copywriter for health supplements.
Generate headlines and descriptions for MGID/Taboola that are:
- COMPELLING: curiosity gaps, fear, authority, social proof
- COMPLIANT: NO 'cures', 'secret', 'doctors hate', 'guaranteed', hard medical claims
- SOFT: Use 'may help', 'research shows', 'supports', not absolute claims

FORBIDDEN PATTERNS: Never use 'doctors hate', 'secret', 'one weird trick', '100% guaranteed', 'cures', 'FDA approved'
✓ GOOD: "Harvard Study: New Brain Support Formula" (authority, soft)
✓ GOOD: "Why 50,000 Doctors Recommend This" (social proof, not doctors hate)
✗ BAD: "Doctors Don't Want You To Know" (conspiracy framing)
✗ BAD: "Cures Memory Loss" (hard medical claim)

Respond with JSON only.""",
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = message.content[0].text
            creatives = self._parse_response(response_text)

            # Check compliance for ALL creatives
            non_compliant = []
            for i, creative in enumerate(creatives):
                violations, is_compliant = self.compliance_checker.check(
                    headline=creative.headline,
                    subheadline=creative.description,
                    body_html="",
                    cta_text="",
                    has_ftc_disclaimer=True,  # Ad copy doesn't need disclaimer itself
                )
                if not is_compliant:
                    non_compliant.append((i, violations))

            if not non_compliant:
                logger.info(f"[creative] ✓ All {len(creatives)} creatives COMPLIANT on attempt {attempt + 1}")
                return CreativeSet(
                    offer_name=offer_name,
                    niche=niche,
                    creatives=creatives,
                    report_used=(report is not None),
                )

            # Log non-compliant creatives and retry
            if attempt < max_retries:
                for idx, violations in non_compliant:
                    v_summary = [f"{v.message}" for v in violations if v.severity == "error"]
                    logger.warning(f"[creative] Creative {idx} non-compliant: {'; '.join(v_summary)}")
            else:
                logger.error(f"[creative] ✗ {len(non_compliant)}/{len(creatives)} still non-compliant after {max_retries} retries")
                logger.warning(f"[creative] Returning {len(creatives) - len(non_compliant)} compliant + {len(non_compliant)} flagged creatives")

        # Return what we have (some or all compliant)
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

    def _build_prompt(self, offer_name: str, niche: str, report: dict | None, vsl_hook: str | None = None, vsl_main_claim: str | None = None, vsl_emotional_trigger: str | None = None) -> str:
        """Build prompt for Claude."""
        base = f"""Generate 8 COMPLIANT native ad creatives for MGID/Taboola.

Offer: {offer_name}
Niche: {niche}

__VSL_CONTEXT__

__DEMO_BLOCK__

STRICT COMPLIANCE RULES:
1. NO hard medical claims: 'cures', 'reverses', 'guaranteed', 'treats disease', 'diagnosed'
   ✓ Use: 'supports', 'may help', 'research shows', 'helps with'
2. NO MGID-forbidden patterns: 'doctors hate', 'secret formula', 'one weird trick', 'hidden'
   ✓ Use: Straightforward benefits, social proof (e.g. "50,000+ Users Say...")
3. NO absolute claims: '100% safe', '100% effective', 'FDA approved'
   ✓ Use: 'FDA-regulated', 'people report', 'studies suggest'

CREATIVE REQUIREMENTS:
- Headline: max 60 chars, curiosity/intrigue, NO forbidden patterns
- Description: max 150 chars, emotional benefit, soft language
- Hook type distribution (CRITICAL — follow exactly):
__HOOK_DISTR__
- Mimic editorial/news content (native ad style)
- Image prompt: Detailed AI generation prompt (for DALL-E/Midjourney)

IMAGE PROMPT GUIDELINES (per hook type):
- CURIOSITY: Mysterious, intriguing imagery (question marks, discovery, eureka moments)
- FEAR: Problem-focused but not scary (tired person, stressed senior, health concern)
- AUTHORITY: Expert/credible imagery (doctor, scientist, research lab, prestigious setting)
- SOCIAL_PROOF: Community/group imagery (happy people, testimonial style, before/after)
- STORY: Narrative imagery (journey, transformation, character-driven, relatable)

Each image_prompt must:
1. Be 600x500px landscape (mention explicitly)
2. Include color palette suggestion (warm/cool/neutral for health)
3. Specify photorealism or illustration style
4. Include mood descriptors (hopeful, professional, trustworthy, etc.)
5. Be AI-generation friendly (compatible with DALL-E 3, Midjourney)
6. **MATCH the demographics block above** — use the specified age, hair, gender, context
7. **INCORPORATE the VSL main_claim and emotional_trigger** when relevant (subtle visual metaphors)

Examples:
✓ AUTHORITY: "Professional photo, 600x500px landscape. Well-dressed doctor or scientist, white coat, in modern clinic setting with technology/charts. Warm, professional lighting. Blue and white color palette. Photorealistic, high quality, trustworthy, credible mood."
✓ SOCIAL_PROOF: "Diverse group of 4-5 happy middle-aged people smiling, 600x500px. Warm golden hour lighting. Natural, joyful expression. Testimonial-style portrait composition. Color palette: warm earth tones + healthy greens. Photorealistic, magazine quality."
✓ CURIOSITY: "Minimalist illustration, 600x500px. Light bulb or discovery icon surrounded by question marks, soft gradients. Modern, clean design. Color palette: soft blues and purples. Digital art style, intriguing mood."

Output JSON (ONLY):
{{"creatives": [
  {{
    "headline": "...",
    "description": "...",
    "hook_type": "...",
    "image_prompt": "Detailed AI prompt here..."
  }}
]}}
"""

        if report:
            patterns = report.get("winning_patterns", [])
            if patterns:
                base += f"\nWinning patterns from competitors (model these):\n"
                for p in patterns[:3]:
                    base += f"- {p}\n"

        # VSL CONTEXT samenstellen
        if vsl_main_claim or vsl_emotional_trigger:
            vsl_ctx_lines = ["VSL CONTEXT (use this for image-prompts and emotional alignment):"]
            if vsl_main_claim:
                vsl_ctx_lines.append(f"- Main claim: {vsl_main_claim}")
            if vsl_emotional_trigger:
                vsl_ctx_lines.append(f"- Emotional trigger: {vsl_emotional_trigger}")
            vsl_ctx_lines.append("Use subtle visual metaphors that match these in your image_prompts.")
            vsl_context_block = "\n".join(vsl_ctx_lines)
        else:
            vsl_context_block = "VSL CONTEXT: (none — generate generic-but-on-niche imagery)"
        base = base.replace("__VSL_CONTEXT__", vsl_context_block)

        # DEMOGRAPHIC BLOCK samenstellen
        demo = _demographics_for_niche(niche)
        demo_block = (
            "TARGET DEMOGRAPHICS (use these in EVERY image_prompt with a human subject):\n"
            f"- Age: {demo['age']}\n"
            f"- Skin tone: {demo['skin_tone']}\n"
            f"- Gender bias: {demo['gender']}\n"
            f"- Hair: {demo['hair']}\n"
            f"- Typical context/setting: {demo['context']}"
        )
        base = base.replace("__DEMO_BLOCK__", demo_block)

        # Hook distribution instructie samenstellen
        VALID_HOOKS = ["curiosity", "fear", "authority", "social_proof", "story"]
        if vsl_hook and vsl_hook.lower() in VALID_HOOKS:
            vh = vsl_hook.lower()
            others = [h for h in VALID_HOOKS if h != vh]
            distr = (
                f"  * 4 creatives with hook_type='{vh}' (matches VSL angle — primary)\n"
                f"  * 1 creative with hook_type='{others[0]}'\n"
                f"  * 1 creative with hook_type='{others[1]}'\n"
                f"  * 1 creative with hook_type='{others[2]}'\n"
                f"  * 1 creative with hook_type='{others[3]}'\n"
                f"  Total: 8 creatives. The 4 '{vh}' creatives MUST emotionally align with "
                f"the VSL's '{vh}' hook for warm-traffic-to-VSL consistency."
            )
        else:
            distr = (
                "  * 2 creatives per hook_type: curiosity, fear, authority, social_proof\n"
                "  * 0 story (only use if specifically requested)\n"
                "  Total: 8 creatives, even spread for clean A/B/C/D testing."
            )
        base = base.replace("__HOOK_DISTR__", distr)
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
                    image_prompt=item.get("image_prompt", "(No image prompt generated)"),
                )
                creatives.append(creative)
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipped invalid creative: {e}")

        return creatives
