#!/usr/bin/env python3
"""
Build script for Vercel: Generate all presell article pages.
Runs during Vercel deployment to ensure articles are up-to-date.
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[build] %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Generate articles and update index."""
    try:
        from src.module4_presell.site_builder import PresellSiteBuilder

        logger.info("Starting build process...")

        builder = PresellSiteBuilder()

        # Ensure site is initialized
        if not builder.is_initialized():
            logger.info("Initializing site...")
            builder.init_site()

        # Update index with all current articles
        logger.info("Updating index.html with all articles...")
        builder.update_index()

        # Count articles
        articles = list(builder.articles_dir.glob("*.html"))
        logger.info(f"✓ Build complete! Found {len(articles)} articles")
        logger.info(f"✓ Site ready at: {builder.site_dir}")

        return 0

    except Exception as e:
        logger.error(f"✗ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
