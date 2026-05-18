"""Build HTML advertorial pages from templates."""

import logging
from datetime import datetime
from pathlib import Path

from .models import PresellPage

logger = logging.getLogger(__name__)


class AdvertorialBuilder:
    """Generate HTML from PresellPage."""

    # Beschikbare layout-varianten — voor A/B testing op visuele layout
    VARIANTS = {
        "news": "advertorial.html",          # Klassieke news-article style (default)
        "story": "advertorial_story.html",   # Personal-reader-story style
    }

    @staticmethod
    def build(page: PresellPage, variant: str = "news") -> str:
        """
        Build HTML string from PresellPage.

        Args:
            page: PresellPage with all content fields
            variant: Layout-variant — "news" (default) of "story"

        Returns:
            HTML string ready to write to file
        """
        template_file = AdvertorialBuilder.VARIANTS.get(variant, AdvertorialBuilder.VARIANTS["news"])
        template_path = Path(__file__).parent / "templates" / template_file
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, encoding="utf-8") as f:
            html = f.read()

        # Map niche to display name
        niche_display = {
            "brain-health": "Brain Health Wellness",
            "lung-health": "Respiratory Health",
            "mens-health": "Men's Health & Vitality",
        }.get(page.niche, page.niche.title())

        # Replace placeholders
        html = html.replace("{OFFER_NAME}", page.offer_name)
        html = html.replace("{HEADLINE}", page.headline)
        html = html.replace("{SUBHEADLINE}", page.subheadline)
        html = html.replace("{NICHE_DISPLAY}", niche_display)
        html = html.replace("{BODY_HTML}", page.body_html)
        html = html.replace("{CTA_TEXT}", page.cta_text)
        html = html.replace("{OFFER_URL}", page.offer_url)

        logger.debug(f"[presell] Built HTML: {len(html)} bytes")
        return html

    @staticmethod
    def build_and_check(page: PresellPage, variant: str = "news") -> tuple[str, list, bool]:
        """Build HTML + compliance-check de FINAL gerenderde pagina.

        Args:
            page: PresellPage
            variant: Layout-variant — "news" of "story"

        Returns:
            (html_string, violations_list, is_compliant)
        """
        from .compliance import ComplianceChecker
        html = AdvertorialBuilder.build(page, variant=variant)
        checker = ComplianceChecker()
        violations, is_compliant = checker.check_html(html)
        if not is_compliant:
            error_count = sum(1 for v in violations if v.severity == "error")
            logger.warning(
                f"[presell] Final HTML compliance: {error_count} errors found "
                f"in rendered template (not just AI-generated body)"
            )
        return html, violations, is_compliant

    @staticmethod
    def save(page: PresellPage, output_dir: Path) -> Path:
        """
        Save PresellPage to HTML file.

        Args:
            page: PresellPage to save
            output_dir: Directory to save in

        Returns:
            Path to saved file
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        niche_slug = page.niche.replace("-", "")
        offer_slug = page.offer_name.lower().replace(" ", "")[:20]
        date_str = page.generated_at.strftime("%Y%m%d")
        filename = f"presell_{niche_slug}_{offer_slug}_{date_str}.html"

        filepath = output_dir / filename

        # Build and save
        html = AdvertorialBuilder.build(page)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"[presell] Saved HTML to {filepath}")
        return filepath
