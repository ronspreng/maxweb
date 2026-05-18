"""Export creatives to ad platform formats (MGID, Taboola, etc)."""

import csv
import os
from io import StringIO
from typing import Optional
from .models import CreativeSet


def _public_image_url(local_path: str, offer_slug: str, site_url: Optional[str] = None) -> str:
    """Transform een lokaal pad naar publieke URL via PRESELL_SITE_URL.

    output/images/bmk/bmk_01_fear.png → {site_url}/ad-images/bmk/bmk_01_fear.png
    """
    if not local_path:
        return ""
    site_url = (site_url or os.environ.get("PRESELL_SITE_URL", "")).strip().rstrip("/")
    if not site_url:
        return local_path  # fallback: lokaal pad
    # Pak alleen de filename
    from pathlib import Path
    filename = Path(local_path).name
    return f"{site_url}/ad-images/{offer_slug}/{filename}"


class CreativeExporter:
    """Export CreativeSet to various ad platform formats."""

    @staticmethod
    def to_mgid_csv(
        creative_set: CreativeSet,
        offer_slug: Optional[str] = None,
        site_url: Optional[str] = None,
        click_url: Optional[str] = None,
    ) -> str:
        """MGID bulk-import CSV.

        MGID's bulk-teaser-importer accepteert deze kolommen:
        - Title (max 75 chars)
        - Description (max 160 chars)
        - Image URL (publiek toegankelijk)
        - Click URL (campagne-tracking-URL, optioneel — meestal in MGID-UI ingesteld)
        - Hook Type (eigen kolom voor jouw eigen overzicht)

        Args:
            creative_set: De CreativeSet uit Module 3
            offer_slug: Voor public-URL-bouw (bv. 'brain-memory-keeper')
            site_url: Override PRESELL_SITE_URL env-var
            click_url: ClickHub campaign URL (e.g. https://petalvane.com/t/<uuid>)

        Returns:
            CSV string ready voor MGID's bulk-uploader
        """
        offer_slug = offer_slug or (creative_set.offer_name or "offer").lower().replace(" ", "-")
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["Title", "Description", "Image URL", "Click URL", "Hook Type"],
        )
        writer.writeheader()
        for creative in creative_set.creatives:
            img_url = _public_image_url(creative.image_url or "", offer_slug, site_url)
            writer.writerow({
                "Title": creative.headline[:75],
                "Description": creative.description[:160],
                "Image URL": img_url,
                "Click URL": click_url or "",
                "Hook Type": creative.hook_type,
            })
        return output.getvalue()

    @staticmethod
    def to_taboola_csv(
        creative_set: CreativeSet,
        offer_slug: Optional[str] = None,
        site_url: Optional[str] = None,
        click_url: Optional[str] = None,
    ) -> str:
        """Taboola bulk-import CSV.

        Taboola format:
        - Headline (max 60 chars)
        - Description (max 150 chars)
        - Image URL (1456x816 recommended)
        - Click URL
        """
        offer_slug = offer_slug or (creative_set.offer_name or "offer").lower().replace(" ", "-")
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["Headline", "Description", "Image URL", "Click URL", "Hook Type"],
        )
        writer.writeheader()
        for creative in creative_set.creatives:
            img_url = _public_image_url(creative.image_url or "", offer_slug, site_url)
            writer.writerow({
                "Headline": creative.headline[:60],
                "Description": creative.description[:150],
                "Image URL": img_url,
                "Click URL": click_url or "",
                "Hook Type": creative.hook_type,
            })
        return output.getvalue()

    @staticmethod
    def to_image_generation_csv(creative_set: CreativeSet) -> str:
        """Just the image-prompts for manual DALL-E/Midjourney use."""
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["Index", "Hook Type", "Headline", "Image Prompt"])
        writer.writeheader()
        for idx, creative in enumerate(creative_set.creatives, 1):
            writer.writerow({
                "Index": idx,
                "Hook Type": creative.hook_type,
                "Headline": creative.headline,
                "Image Prompt": creative.image_prompt,
            })
        return output.getvalue()
