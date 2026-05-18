#!/usr/bin/env python3
"""
Build script for Vercel: Generate all presell article pages.
Runs during Vercel deployment to ensure articles are up-to-date.
"""

import logging
import sys
import os
from pathlib import Path

# Ensure we're in the right directory
project_root = Path(__file__).parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='[build] %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Generate articles and update index."""
    try:
        from src.module4_presell.site_builder import PresellSiteBuilder
        from datetime import datetime

        logger.info(f"Working directory: {os.getcwd()}")
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
        logger.info(f"  Articles dir: {builder.articles_dir}")
        logger.info(f"  Articles dir exists: {builder.articles_dir.exists()}")

        all_articles = list(builder.articles_dir.glob("*.html"))
        logger.info(f"  Found {len(all_articles)} articles before update")

        # Log ALL articles found
        for art in sorted(all_articles):
            logger.info(f"    - {art.name}")

        # Add HTML wrapper with stylesheet to articles (preserve original structure)
        logger.info("Adding HTML wrapper to articles...")
        from datetime import datetime as dt
        for article_file in builder.articles_dir.glob("*.html"):
            with open(article_file, "r", encoding="utf-8") as f:
                article_html = f.read()

            # Only wrap if it doesn't already have DOCTYPE
            if "<!DOCTYPE" not in article_html:
                article_title = article_file.stem.replace("-", " ").title()
                # Minimal wrapper - just add HTML structure, keep article as-is
                wrapped_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article_title} - Health & Wellness</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <header class="site-header">
        <div class="container">
            <a href="/" class="logo">Health & Wellness</a>
            <nav>
                <a href="/">All Articles</a>
            </nav>
        </div>
    </header>

    {article_html}

    <footer class="site-footer">
        <div class="container">
            <p>&copy; {dt.now().year} Health & Wellness. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>"""
                with open(article_file, "w", encoding="utf-8") as f:
                    f.write(wrapped_html)
                logger.info(f"  Wrapped: {article_file.name}")

        builder.update_index()

        logger.info("  Index updated successfully")

        # Count articles
        articles = list(builder.articles_dir.glob("*.html"))
        final_count = len(articles)
        logger.info(f"✓ Build complete! Found {final_count} articles")
        logger.info(f"✓ Site ready at: {builder.site_dir}")

        # Warning if fewer than expected
        if final_count < 18:
            logger.warning(f"⚠️  Expected 18 articles, found {final_count}")
            logger.warning("Missing articles:")
            expected = [
                "blue-light-sleep-cognition.html",
                "brain-health-101.html",
                "brain-memory-keeper.html",
                "cognitive-training-mental-games.html",
                "exercise-for-brain-health.html",
                "gut-brain-connection.html",
                "hydration-brain-function.html",
                "meditation-mindfulness-brain.html",
                "memory-and-aging.html",
                "natural-ways-to-boost-focus.html",
                "nutrition-for-brain-power.html",
                "preventing-cognitive-decline-aging.html",
                "sleep-and-cognitive-function.html",
                "stress-and-brain-health.html",
                "supplements-cognitive-support.html",
                "test-article-123.html",
                "test-article-456.html",
                "understanding-cognitive-decline.html",
            ]
            found_names = {art.name for art in articles}
            for exp in expected:
                if exp not in found_names:
                    logger.warning(f"  - {exp}")

        return 0

    except Exception as e:
        logger.error(f"✗ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
