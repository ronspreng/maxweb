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
        from datetime import datetime

        logger.info("Starting build process...")

        builder = PresellSiteBuilder()

        # Ensure site is initialized
        if not builder.is_initialized():
            logger.info("Initializing site...")
            builder.init_site()

        # Always reset index.html to template (important for update_index() to work)
        # This ensures new articles are discovered
        logger.info("Resetting index.html template...")
        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Expert health and wellness insights from trusted sources.">
    <title>Health & Wellness - Expert Insights & Wellness Tips</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <header class="site-header">
        <div class="container">
            <div>
                <h1 class="logo">Health & Wellness</h1>
                <p class="tagline">Expert insights and wellness tips</p>
            </div>
            <nav>
                <a href="/">Home</a>
                <a href="/about.html">About</a>
                <a href="/disclaimer.html">Disclaimer</a>
                <a href="/privacy-policy.html">Privacy</a>
                <a href="/terms-of-service.html">Terms</a>
                <a href="/contact.html">Contact</a>
            </nav>
        </div>
    </header>

    <section class="hero-section">
        <div class="container">
            <h1>Optimize Your Health & Wellness</h1>
            <p>Explore evidence-based insights on brain health, nutrition, exercise, and more. Discover practical strategies to enhance your cognitive function and overall well-being.</p>
            <div style="margin-top: 25px;">
                <span class="badge">Evidence-Based Research</span>
                <span class="badge">Expert Reviewed</span>
                <span class="badge">Medically Accurate</span>
            </div>
        </div>
    </section>

    <main class="container">
        <section class="articles-grid">
            <h1>Latest Articles</h1>
            <div class="article-list">
                <!-- Articles will be added here -->
            </div>
        </section>
    </main>

    <footer class="site-footer">
        <div class="container">
            <p>&copy; {datetime.now().year} Health & Wellness. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>"""

        index_path = builder.site_dir / "index.html"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_html)

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
