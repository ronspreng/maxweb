"""MGID + FTC compliance checker for advertorial copy."""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ComplianceViolation:
    """A single compliance violation."""

    violation_type: str  # "hard_claim", "forbidden_pattern", "missing_disclaimer"
    severity: str  # "error", "warning"
    message: str
    location: str  # "headline", "subheadline", "body", "global"
    suggested_fix: Optional[str] = None


class ComplianceChecker:
    """Validates advertorial copy against MGID + FTC standards."""

    # Hard medical claims (FTC violation)
    HARD_CLAIMS = {
        r"\bcures?\b": "Replace with 'supports', 'promotes', or 'helps with'",
        r"\breverse[ds]?\b": "Replace with 'may help improve' or 'supports'",
        r"\bguarantees?\b": "Replace with 'designed to help' or 'may help'",
        r"\bdiagnose[ds]?\b": "Remove - only medical professionals can diagnose",
        r"\btreat[s]?\b (disease|cancer|diabetes|heart|stroke)": "Replace with 'supports health'",
        r"\bfda\s+approved\b": "FDA doesn't approve supplements - use 'FDA-regulated'",
        r"\b100%\s+(effective|safe|cure)": "Remove absolute claims",
        r"\bmedically?\s+(proven|tested)\b": "Use 'research shows' or 'studies suggest'",
    }

    # MGID-specific forbidden patterns (AI-screened)
    FORBIDDEN_PATTERNS = {
        r"\bdoctors?\s+(hate|don't want|don't want you to know)": "MGID blocks 'doctors hate' framing",
        r"\bsecret\s+(formula|ingredient|cure)": "MGID blocks 'secret' language",
        r"\bone\s+weird\s+trick": "Outdated clickbait - MGID flags this",
        r"\b(pharmaceutical|big pharma|pharma)\s+(don't want|doesn't want|hiding)": "MGID blocks pharma conspiracy angles",
        r"\blimited\s+time\s+offer\b": "MGID restricts artificial urgency (unless genuinely limited)",
        r"\bdon't\s+let.*know": "Remove conspiracy framing",
    }

    # FTC disclaimer check
    FTC_DISCLAIMER_KEYWORDS = {"results may vary", "advertisement", "affiliate", "disclosure", "terms"}

    def check(
        self,
        headline: str,
        subheadline: str,
        body_html: str,
        cta_text: str,
        has_ftc_disclaimer: bool | None = None,
    ) -> tuple[list[ComplianceViolation], bool]:
        """
        Check advertorial copy for compliance.

        Args:
            headline: Main headline
            subheadline: Subheadline
            body_html: HTML body content
            cta_text: CTA button text
            has_ftc_disclaimer: Whether page includes FTC disclaimer

        Returns:
            (violations list, is_compliant bool)
        """
        violations = []

        # Check headline
        violations.extend(self._check_text(headline, "headline"))

        # Check subheadline
        violations.extend(self._check_text(subheadline, "subheadline"))

        # Check body (strip HTML tags first)
        body_text = self._strip_html(body_html)
        violations.extend(self._check_text(body_text, "body"))

        # Check CTA
        violations.extend(self._check_text(cta_text, "cta"))

        # Auto-detect FTC disclaimer als niet expliciet meegegeven
        if has_ftc_disclaimer is None:
            body_text = self._strip_html(body_html)
            has_ftc_disclaimer = self._has_ftc_keywords(body_text)

        # Check FTC disclaimer
        if not has_ftc_disclaimer:
            violations.append(
                ComplianceViolation(
                    violation_type="missing_disclaimer",
                    severity="error",
                    message="No FTC disclaimer found. Required: 'Results may vary. This is an advertisement.'",
                    location="global",
                    suggested_fix="Add to page footer: <p><small>Results may vary. This is an advertisement.</small></p>",
                )
            )

        # Determine overall compliance
        is_compliant = not any(v.severity == "error" for v in violations)

        return violations, is_compliant

    def check_html(self, full_html: str) -> tuple[list[ComplianceViolation], bool]:
        """Check een COMPLETE gerenderde HTML-pagina (template + content).

        Strip alle HTML, run alle pattern-checks, auto-detect FTC-disclaimer
        vanuit de zichtbare tekst. Gebruik dit na AdvertorialBuilder.build()
        om template-issues te vangen die in de generator-check niet zichtbaar waren.

        Args:
            full_html: De volledige HTML-string van de gerenderde pagina

        Returns:
            (violations, is_compliant)
        """
        text = self._strip_html(full_html)
        violations = list(self._check_text(text, "full_page"))

        # Auto-detect FTC-disclaimer
        if not self._has_ftc_keywords(text):
            violations.append(
                ComplianceViolation(
                    violation_type="missing_disclaimer",
                    severity="error",
                    message="No FTC disclaimer detected in page. Required keywords: 'results may vary', 'advertisement', 'affiliate', 'disclosure'.",
                    location="full_page",
                    suggested_fix="Add a footer with: 'Results may vary. This is an advertisement.'",
                )
            )

        is_compliant = not any(v.severity == "error" for v in violations)
        return violations, is_compliant

    def _has_ftc_keywords(self, text: str) -> bool:
        """Returns True als minstens 1 FTC-disclaimer-keyword in de tekst staat."""
        low = text.lower()
        return any(kw in low for kw in self.FTC_DISCLAIMER_KEYWORDS)

    def _check_text(self, text: str, location: str) -> list[ComplianceViolation]:
        """Check a text section against all rules."""
        violations = []
        text_lower = text.lower()

        # Check hard medical claims
        for pattern, fix in self.HARD_CLAIMS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                match = re.search(pattern, text_lower, re.IGNORECASE)
                violations.append(
                    ComplianceViolation(
                        violation_type="hard_claim",
                        severity="error",
                        message=f"Hard medical claim detected: '{match.group()}' violates FTC guidelines",
                        location=location,
                        suggested_fix=fix,
                    )
                )

        # Check MGID forbidden patterns
        for pattern, reason in self.FORBIDDEN_PATTERNS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                match = re.search(pattern, text_lower, re.IGNORECASE)
                violations.append(
                    ComplianceViolation(
                        violation_type="forbidden_pattern",
                        severity="error",
                        message=f"MGID blocks this: '{match.group()}' — {reason}",
                        location=location,
                        suggested_fix="Remove or rephrase to be more straightforward",
                    )
                )

        return violations

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from text."""
        return re.sub(r"<[^>]+>", " ", html)

    def report(self, violations: list[ComplianceViolation], is_compliant: bool) -> str:
        """Format violations as a human-readable report."""
        if not violations:
            return "✅ All compliance checks passed!"

        lines = []
        if is_compliant:
            lines.append("⚠️  Warnings (but compliant):")
        else:
            lines.append("❌ COMPLIANCE VIOLATIONS - MUST FIX BEFORE PUBLISH:")

        for v in violations:
            lines.append(f"\n  [{v.severity.upper()}] {v.location.upper()}")
            lines.append(f"  Issue: {v.message}")
            if v.suggested_fix:
                lines.append(f"  Fix: {v.suggested_fix}")

        return "\n".join(lines)
