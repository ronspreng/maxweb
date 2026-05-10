"""Build HTML advertorial pages from templates."""

import logging
from datetime import datetime
from pathlib import Path

from .models import PresellPage

logger = logging.getLogger(__name__)


class AdvertorialBuilder:
    """Generate HTML from PresellPage."""

    @staticmethod
    def build(page: PresellPage) -> str:
        """
        Build HTML string from PresellPage.

        Args:
            page: PresellPage with all content fields

        Returns:
            HTML string ready to write to file
        """
        template_path = Path(__file__).parent / "templates" / "advertorial.html"
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
