"""
Deduplication logic for collected native ads.
"""

import json
import logging
from pathlib import Path

from .models import NativeAd

logger = logging.getLogger(__name__)


class AdDeduplicator:
    """Deduplicates ads by fingerprint, with optional JSON cache persistence."""

    def __init__(self, cache_path: Path | None = None) -> None:
        self._seen: set[str] = set()
        self.cache_path = cache_path
        if cache_path and cache_path.exists():
            self._load_cache(cache_path)

    def deduplicate(self, ads: list[NativeAd]) -> list[NativeAd]:
        """Return only ads not seen before. Updates internal seen set."""
        unique = []
        for ad in ads:
            if ad.fingerprint not in self._seen:
                self._seen.add(ad.fingerprint)
                unique.append(ad)
        logger.info(f"Dedup: {len(ads)} in → {len(unique)} unique")
        return unique

    def save_cache(self, ads: list[NativeAd]) -> None:
        """Persist all seen ads to JSON cache for incremental runs."""
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(
                [ad.model_dump(mode="json") for ad in ads],
                f,
                indent=2,
                default=str,
            )
        logger.info(f"Saved {len(ads)} ads to cache: {self.cache_path}")

    def _load_cache(self, path: Path) -> None:
        """Load fingerprints from existing cache file."""
        with open(path, encoding="utf-8") as f:
            cached = json.load(f)
        for item in cached:
            self._seen.add(item["fingerprint"])
        logger.info(f"Loaded {len(self._seen)} fingerprints from cache")
