"""Publish generated ad-images to public hosting via existing presell_site Vercel deploy.

Strategy: copy PNGs naar output/presell_site/ad-images/<offer>/, dan git add+commit+push.
Vercel pikt automatisch de push op en serveert via PRESELL_SITE_URL.

Public URL wordt: {PRESELL_SITE_URL}/ad-images/{offer_slug}/{filename}.png
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import CreativeSet

logger = logging.getLogger(__name__)


class ImagePublisher:
    """Publish ad-images to the presell-site Vercel deployment."""

    AD_IMAGES_SUBPATH = "ad-images"

    @staticmethod
    def publish_images_for_offer(
        offer_slug: str,
        local_images_dir: Path,
        site_url: Optional[str] = None,
        commit_message: Optional[str] = None,
        auto_push: bool = True,
    ) -> dict:
        """Copy alle PNG-images uit local_images_dir → presell_site/ad-images/<offer_slug>/.
        Daarna git add + commit + push (als auto_push=True).

        Args:
            offer_slug: URL-safe naam (e.g. 'brain-memory-keeper')
            local_images_dir: Bron-map met *.png-files (typisch output/images/<slug>)
            site_url: Public base URL (anders uit env PRESELL_SITE_URL gelezen)
            commit_message: Git commit-msg (auto als None)
            auto_push: Commit + push naar GitHub (Vercel auto-deploys)

        Returns:
            Dict met: copied (count), public_urls (list of str), success (bool)
        """
        site_url = (site_url or os.environ.get("PRESELL_SITE_URL", "")).strip().rstrip("/")
        if not site_url:
            logger.warning("PRESELL_SITE_URL niet gezet — URLs in MGID-CSV zullen relatief zijn")

        # Bron-validatie
        local_images_dir = Path(local_images_dir)
        if not local_images_dir.exists():
            return {"success": False, "copied": 0, "public_urls": [],
                    "error": f"Local images dir bestaat niet: {local_images_dir}"}

        png_files = sorted(local_images_dir.glob("*.png"))
        if not png_files:
            return {"success": False, "copied": 0, "public_urls": [],
                    "error": f"Geen PNG-files in {local_images_dir}"}

        # Doel: presell_site/ad-images/<slug>/
        target_dir = Path("output/presell_site") / ImagePublisher.AD_IMAGES_SUBPATH / offer_slug
        target_dir.mkdir(parents=True, exist_ok=True)

        public_urls = []
        copied = 0
        for src in png_files:
            dst = target_dir / src.name
            shutil.copy2(src, dst)
            copied += 1
            if site_url:
                public_url = f"{site_url}/{ImagePublisher.AD_IMAGES_SUBPATH}/{offer_slug}/{src.name}"
            else:
                public_url = f"/{ImagePublisher.AD_IMAGES_SUBPATH}/{offer_slug}/{src.name}"
            public_urls.append(public_url)

        logger.info(f"[image-publisher] Copied {copied} images → {target_dir}")

        if not auto_push:
            return {"success": True, "copied": copied, "public_urls": public_urls,
                    "committed": False}

        # Git add + commit + push
        try:
            subprocess.run(
                ["git", "add", "-f", str(target_dir)],
                check=True, capture_output=True, cwd=".",
            )
            msg = commit_message or f"Publish ad-images for {offer_slug} ({datetime.utcnow():%Y-%m-%d %H:%M})"
            r = subprocess.run(
                ["git", "commit", "-m", msg],
                capture_output=True, cwd=".", text=True,
            )
            if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr).lower():
                return {"success": False, "copied": copied, "public_urls": public_urls,
                        "error": f"git commit failed: {r.stderr[:200]}"}
            r = subprocess.run(
                ["git", "push"],
                capture_output=True, cwd=".", text=True,
            )
            if r.returncode != 0:
                return {"success": False, "copied": copied, "public_urls": public_urls,
                        "error": f"git push failed: {r.stderr[:200]}"}
            logger.info(f"[image-publisher] Pushed to remote — Vercel zal deployment starten")
            return {"success": True, "copied": copied, "public_urls": public_urls,
                    "committed": True, "deploy_note": "Vercel deployment 1-3 min — daarna live"}
        except subprocess.CalledProcessError as exc:
            return {"success": False, "copied": copied, "public_urls": public_urls,
                    "error": f"Git error: {exc}"}
