"""AI-powered compliance violation fixer.

Gebruikt Claude Haiku om body_html te herschrijven zodat compliance-violations
verdwijnen, terwijl betekenis + tone behouden blijft.

Cost per fix: ~$0.001-0.002 (Haiku, ~1k tokens). Vergeleken met handmatig
herschrijven of een volledige nieuwe AdvertorialGenerator-run is dit veel
goedkoper én vele malen sneller.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .compliance import ComplianceChecker, ComplianceViolation
from .models import PresellPage

logger = logging.getLogger(__name__)


class ComplianceFixer:
    """Auto-fix compliance violations via Claude Haiku."""

    DEFAULT_MODEL = "claude-haiku-4-5-20251001"
    MAX_FIX_ATTEMPTS = 2

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package niet geinstalleerd. Run: pip install anthropic"
            ) from exc

        key = (api_key or os.environ.get("ANTHROPIC_API_KEY", "")).strip()
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY niet gezet.")

        self.client = Anthropic(api_key=key)
        self.model = model or self.DEFAULT_MODEL
        self.checker = ComplianceChecker()

    def fix_page(
        self,
        page: PresellPage,
        violations: list[ComplianceViolation],
    ) -> tuple[PresellPage, list[ComplianceViolation], bool]:
        """Probeer alle violations te fixen via re-write.

        Args:
            page: PresellPage met violations
            violations: Lijst van violations (uit ComplianceChecker.check_html / check)

        Returns:
            (updated_page, remaining_violations, is_now_compliant)
        """
        # Filter: alleen 'error'-level content-violations zijn auto-fixable.
        # 'missing_disclaimer' is een template-issue, niet via tekst-rewrite oplosbaar.
        fixable = [
            v for v in violations
            if v.severity == "error" and v.violation_type in ("hard_claim", "forbidden_pattern")
        ]
        if not fixable:
            logger.info("[fixer] Geen auto-fixable violations (alleen disclaimer/structuur)")
            return page, violations, False

        for attempt in range(1, self.MAX_FIX_ATTEMPTS + 1):
            logger.info(f"[fixer] Fix-attempt {attempt}/{self.MAX_FIX_ATTEMPTS}")
            try:
                rewrites = self._rewrite_via_claude(page, fixable)
            except Exception as exc:
                logger.error(f"[fixer] Claude rewrite failed: {type(exc).__name__}: {exc}")
                return page, violations, False

            # Pas de rewrites toe op de page-fields
            if "headline" in rewrites:
                page.headline = rewrites["headline"]
            if "subheadline" in rewrites:
                page.subheadline = rewrites["subheadline"]
            if "body_html" in rewrites:
                page.body_html = rewrites["body_html"]
            if "cta_text" in rewrites:
                page.cta_text = rewrites["cta_text"]

            # Re-check
            new_violations, is_compliant = self.checker.check(
                headline=page.headline,
                subheadline=page.subheadline,
                body_html=page.body_html,
                cta_text=page.cta_text,
                has_ftc_disclaimer=None,  # auto-detect
            )

            if is_compliant:
                logger.info(f"[fixer] ✓ Compliant na attempt {attempt}")
                return page, new_violations, True

            # Filter opnieuw — misschien fixt Claude er een, maar introduceert een andere
            remaining_fixable = [
                v for v in new_violations
                if v.severity == "error" and v.violation_type in ("hard_claim", "forbidden_pattern")
            ]
            if not remaining_fixable:
                # Niet compliant maar alleen niet-fixable (disclaimer) over
                logger.info(f"[fixer] Content-violations gefixt, alleen template-issues over")
                return page, new_violations, False

            fixable = remaining_fixable

        logger.warning(f"[fixer] Niet kunnen fixen na {self.MAX_FIX_ATTEMPTS} attempts")
        return page, new_violations, False

    def _rewrite_via_claude(
        self,
        page: PresellPage,
        violations: list[ComplianceViolation],
    ) -> dict[str, str]:
        """Vraag Claude de relevante velden te herschrijven.

        Returns:
            Dict met optioneel 'headline', 'subheadline', 'body_html', 'cta_text'
            keys — alleen velden die ge-rewrite moesten worden.
        """
        # Groepeer violations per location
        by_loc: dict[str, list[ComplianceViolation]] = {}
        for v in violations:
            by_loc.setdefault(v.location, []).append(v)

        # Bouw violation-summary per locatie
        viol_blocks = []
        for loc, vs in by_loc.items():
            lines = [f"Location: {loc}"]
            for v in vs:
                fix_hint = f" (suggested fix: {v.suggested_fix})" if v.suggested_fix else ""
                lines.append(f"  - {v.message}{fix_hint}")
            viol_blocks.append("\n".join(lines))

        viol_text = "\n\n".join(viol_blocks)

        # Bouw input-dict met huidige content
        current_fields = {
            "headline": page.headline,
            "subheadline": page.subheadline,
            "body_html": page.body_html,
            "cta_text": page.cta_text,
        }

        # Alleen velden meegeven die violations hebben (efficiency + focus)
        affected_locations = set(by_loc.keys())
        # Map ComplianceChecker's location-names op page-field-names
        location_to_field = {
            "headline": "headline",
            "subheadline": "subheadline",
            "body": "body_html",
            "cta": "cta_text",
            "full_page": None,  # alle velden
        }
        fields_to_rewrite = set()
        for loc in affected_locations:
            field_key = location_to_field.get(loc)
            if field_key is None:
                # full_page → rewrite alles
                fields_to_rewrite = set(current_fields.keys())
                break
            else:
                fields_to_rewrite.add(field_key)

        # Bouw prompt
        fields_block = "\n\n".join(
            f"--- {fname} (current) ---\n{current_fields[fname]}"
            for fname in fields_to_rewrite if current_fields.get(fname)
        )

        prompt = f"""You are a copywriter fixing compliance violations in advertorial copy.

VIOLATIONS DETECTED:
{viol_text}

CURRENT CONTENT (the affected fields):
{fields_block}

YOUR TASK:
Rewrite the affected fields to fix ALL violations while:
1. Keeping the same intent, tone, and emotional appeal
2. Using soft, FTC-compliant language ("supports", "may help", "research shows" instead of "cures", "guaranteed", "100% effective")
3. NOT introducing new violations (no "doctors hate", "secret", "one weird trick", "limited time")
4. Preserving the structure (e.g., body_html keeps its <p> tags)
5. NOT changing length dramatically

Output ONLY valid JSON with the rewritten fields. Include only fields you changed:
{{
  "headline": "...",
  "subheadline": "...",
  "body_html": "...",
  "cta_text": "..."
}}

Do not include any explanation, only the JSON."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system="You are a compliance-focused copywriter. Output only valid JSON.",
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences als die er zijn
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()

        import json
        try:
            rewrites = json.loads(raw)
            if not isinstance(rewrites, dict):
                raise ValueError("Expected JSON object")
            # Filter keys: alleen toestaan wat we vragen
            allowed_keys = {"headline", "subheadline", "body_html", "cta_text"}
            return {k: v for k, v in rewrites.items() if k in allowed_keys and isinstance(v, str)}
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(f"[fixer] JSON parse failed: {exc}\nRaw: {raw[:300]}")
            raise
