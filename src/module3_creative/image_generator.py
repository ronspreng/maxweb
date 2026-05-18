"""Generate native-ad images via OpenAI gpt-image-2.

DALL-E 3 is door OpenAI vervangen door gpt-image-* familie (2025-2026). gpt-image-2
is de nieuwste (april 2026), met betere prompt-following en text-rendering.

Cost (OpenAI 2026 pricing voor gpt-image-2):
- low:    $0.011 per 1024x1024  (~$0.015 voor 1536x1024)
- medium: $0.042 per 1024x1024  (~$0.058 voor 1536x1024)
- high:   $0.167 per 1024x1024  (~$0.230 voor 1536x1024)

Voor batch van 8 creatives bij 'medium' (sweet spot voor native ads):
8 × $0.058 = ~$0.46 per offer.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .models import CreativeSet, NativeAdCreative

logger = logging.getLogger(__name__)


@dataclass
class ImageGenerationResult:
    creative_index: int
    success: bool
    image_url: Optional[str] = None
    local_path: Optional[str] = None
    error: Optional[str] = None
    cost_estimate_usd: float = 0.0


@dataclass
class BatchResult:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    results: list[ImageGenerationResult] = field(default_factory=list)
    total_cost_usd: float = 0.0


class ImageGenerator:
    """Generate images for NativeAdCreatives via gpt-image-2.

    Usage:
        gen = ImageGenerator()
        result = gen.generate_for_creative_set(
            creative_set,
            output_dir=Path("output/images"),
            offer_slug="brain-memory-keeper",
        )
    """

    # gpt-image-2 sizes (landscape voor native ads)
    SIZE_LANDSCAPE = "1536x1024"   # native-ad-compatible
    SIZE_SQUARE = "1024x1024"
    SIZE_PORTRAIT = "1024x1536"

    # gpt-image-2 qualities
    QUALITY_LOW = "low"
    QUALITY_MEDIUM = "medium"
    QUALITY_HIGH = "high"

    # Pricing (USD per image, gpt-image-2 @ 1536x1024 landscape, OpenAI 2026)
    PRICING = {
        QUALITY_LOW: 0.015,
        QUALITY_MEDIUM: 0.058,
        QUALITY_HIGH: 0.230,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-image-2",
    ):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai package is niet geinstalleerd. Run: pip install openai"
            ) from exc

        self.model = model
        key = (api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY niet gezet. Voeg toe aan .env."
            )
        self.client = OpenAI(api_key=key)

    def generate_one(
        self,
        prompt: str,
        size: str = SIZE_LANDSCAPE,
        quality: str = QUALITY_MEDIUM,
    ) -> Optional[bytes]:
        """Genereer 1 image, return PNG bytes (decoded uit base64) of None.

        gpt-image-2 returnt base64 by default — gen returnt direct bytes
        zodat de caller meteen naar disk kan schrijven.
        """
        try:
            resp = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
            b64 = resp.data[0].b64_json
            if not b64:
                logger.error("[image-gen] gpt-image response had no b64_json")
                return None
            return base64.b64decode(b64)
        except Exception as exc:
            logger.error(f"[image-gen] gpt-image call failed: {type(exc).__name__}: {exc}")
            return None

    def generate_for_creative_set(
        self,
        creative_set: CreativeSet,
        output_dir: Path,
        offer_slug: str = "offer",
        quality: str = QUALITY_MEDIUM,
        size: str = SIZE_LANDSCAPE,
        progress_callback=None,
    ) -> BatchResult:
        """Genereer images voor alle creatives. Slaat lokaal op, update image_url
        veld naar relatief pad (file:///... of relatief tov project root).

        Args:
            creative_set: CreativeSet uit Module 3
            output_dir: Map voor PNG-bestanden
            offer_slug: Korte naam voor filenames
            quality: low/medium/high
            size: 1536x1024 (landscape) / 1024x1024 (square) / 1024x1536 (portrait)
            progress_callback: fn(idx, total, status) voor Streamlit progress

        Returns:
            BatchResult met cost en file-paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        unit_price = self.PRICING.get(quality, self.PRICING[self.QUALITY_MEDIUM])
        batch = BatchResult(total=len(creative_set.creatives))

        for idx, creative in enumerate(creative_set.creatives):
            if progress_callback:
                progress_callback(idx, batch.total, "starting")

            png_bytes = self.generate_one(creative.image_prompt, size=size, quality=quality)
            if not png_bytes:
                batch.failed += 1
                batch.results.append(
                    ImageGenerationResult(
                        creative_index=idx,
                        success=False,
                        error="gpt-image API call failed (zie logs)",
                    )
                )
                if progress_callback:
                    progress_callback(idx, batch.total, "failed")
                continue

            # Lokale opslag
            safe_hook = (creative.hook_type or "x").replace(" ", "-")
            filename = f"{offer_slug}_{idx + 1:02d}_{safe_hook}.png"
            local_path = output_dir / filename
            local_path.write_bytes(png_bytes)

            # Update creative.image_url naar lokale path
            # (Streamlit kan lokale PNG-bestanden direct in st.image() laden)
            creative.image_url = str(local_path)

            batch.succeeded += 1
            batch.total_cost_usd += unit_price
            batch.results.append(
                ImageGenerationResult(
                    creative_index=idx,
                    success=True,
                    image_url=None,
                    local_path=str(local_path),
                    cost_estimate_usd=unit_price,
                )
            )
            if progress_callback:
                progress_callback(idx, batch.total, "done")

        logger.info(
            f"[image-gen] Done: {batch.succeeded}/{batch.total} succeeded, "
            f"cost ~${batch.total_cost_usd:.2f}"
        )
        return batch
