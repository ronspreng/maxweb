"""Build a static presell website from presell pages."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import PresellPage

logger = logging.getLogger(__name__)


class PresellSiteBuilder:
    """Manage a static presell website."""

    def __init__(self, site_dir: Path = Path("output/presell_site")):
        self.site_dir = site_dir
        self.articles_dir = site_dir / "articles"

    def init_site(self) -> Path:
        """Initialize empty website template (one-time setup)."""
        self.site_dir.mkdir(parents=True, exist_ok=True)
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        self.generate_css()
        self._generate_empty_index()
        self.generate_sitemap()
        logger.info(f"[site] Initialized empty site at {self.site_dir}")
        return self.site_dir

    def is_initialized(self) -> bool:
        """Check if site has been initialized."""
        return (self.site_dir / "index.html").exists()

    def _generate_empty_index(self) -> Path:
        """Generate empty index.html template."""
        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Health & Wellness - Articles</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <header class="site-header">
        <div class="container">
            <h1 class="logo">Health & Wellness</h1>
            <p class="tagline">Expert insights and wellness tips</p>
        </div>
    </header>

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

        index_path = self.site_dir / "index.html"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_html)

        logger.info(f"[site] Generated empty index.html")
        return index_path

    def add_article(self, page: PresellPage, article_html: str) -> Path:
        """
        Add presell page as article to site.
        Saves article and updates index.html.

        Args:
            page: PresellPage model
            article_html: Generated HTML content

        Returns:
            Path to saved article
        """
        # Generate article filename
        slug = page.offer_name.lower().replace(" ", "-").replace("'", "")
        filename = f"{slug}.html"
        filepath = self.articles_dir / filename

        # Wrap in article template with navigation
        html = self._wrap_article(page, article_html, slug)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"[site] Added article: {filename}")

        # Update index listing
        self.update_index()

        return filepath

    def _wrap_article(self, page: PresellPage, body_html: str, slug: str) -> str:
        """Wrap presell page in article template with navigation."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page.offer_name} - Health & Wellness</title>
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

    <main class="container article-container">
        <article class="article">
            {body_html}
        </article>
    </main>

    <footer class="site-footer">
        <div class="container">
            <p>&copy; {datetime.now().year} Health & Wellness. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>"""

    def update_index(self) -> Path:
        """
        Update index.html with current article listing.
        Adds articles without regenerating entire page.

        Returns:
            Path to index.html
        """
        # Find all articles
        articles = list(self.articles_dir.glob("*.html"))
        article_items = []

        for article_file in sorted(articles):
            slug = article_file.stem

            # Extract title from HTML <h1> tag (the actual headline)
            title = slug.replace("-", " ").title()
            try:
                with open(article_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Try H1 first (presell pages use this for the hook headline)
                    match = re.search(r"<h1>\s*([^<]+?)\s*</h1>", content, re.IGNORECASE)
                    if match:
                        title = match.group(1).strip()
                    else:
                        # Fallback to title tag for other pages
                        match = re.search(r"<title>\s*([^<]+?)\s*</title>", content, re.IGNORECASE)
                        if match:
                            full_title = match.group(1).strip()
                            # Remove trailing " - Health & Wellness" or " - Health Intelligence"
                            title = re.sub(r"\s*-\s*[A-Za-z\s&]+$", "", full_title).strip()
            except Exception as e:
                logger.warning(f"Could not extract title from {article_file}: {e}")

            category = "Health" if "brain" in slug or "cognitive" in slug or "memory" in slug else "Wellness"
            article_items.append(f"""                <article class="article-card">
                    <div class="article-card-content">
                        <div class="article-card-meta">
                            <span>{category}</span>
                            <span>Read in 5 min</span>
                        </div>
                        <h3><a href="/articles/{slug}.html">{title}</a></h3>
                        <p>Discover the latest in health and wellness insights and practical strategies.</p>
                        <a href="/articles/{slug}.html" class="btn">Read More</a>
                    </div>
                </article>""")

        articles_html = "\n".join(article_items) if article_items else """            <div class="article-card">
                <p>No articles yet. Create your first presell page to get started!</p>
            </div>"""

        # Read existing index
        index_path = self.site_dir / "index.html"
        with open(index_path, "r", encoding="utf-8") as f:
            index_content = f.read()

        # Replace article list placeholder
        updated = index_content.replace(
            "                <!-- Articles will be added here -->",
            articles_html
        )

        # Write back
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(updated)

        logger.info(f"[site] Updated index.html ({len(articles)} articles)")
        return index_path

    def generate_css(self) -> Path:
        """Generate shared CSS stylesheet."""
        css_dir = self.site_dir / "css"
        css_dir.mkdir(parents=True, exist_ok=True)

        css_content = """/* Presell Site Stylesheet */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --primary: #2c3e50;
    --secondary: #3498db;
    --accent: #e74c3c;
    --light: #f8f9fa;
    --text: #333;
    --border: #ddd;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: #fff;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Header */
.site-header {
    background: var(--primary);
    color: white;
    padding: 20px 0;
    margin-bottom: 40px;
    border-bottom: 3px solid var(--secondary);
}

.site-header .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.logo {
    font-size: 24px;
    font-weight: bold;
    color: white;
    text-decoration: none;
}

.tagline {
    font-size: 14px;
    opacity: 0.9;
    margin-top: 5px;
}

nav a {
    color: white;
    text-decoration: none;
    margin-left: 30px;
    transition: opacity 0.2s;
}

nav a:hover {
    opacity: 0.8;
}

/* Articles Grid */
.articles-grid h1 {
    margin-bottom: 30px;
    font-size: 32px;
}

.articles-grid {
    margin: 60px 0;
}

.article-card {
    border: 1px solid var(--border);
    padding: 30px;
    margin-bottom: 30px;
    border-radius: 8px;
    transition: box-shadow 0.2s;
}

.article-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.article-card h2 {
    margin-bottom: 10px;
}

.article-card h2 a {
    color: var(--secondary);
    text-decoration: none;
}

.article-card h2 a:hover {
    text-decoration: underline;
}

.article-card p {
    color: #666;
    margin-bottom: 15px;
}

.btn {
    display: inline-block;
    background: var(--secondary);
    color: white;
    padding: 10px 20px;
    text-decoration: none;
    border-radius: 4px;
    transition: background 0.2s;
}

.btn:hover {
    background: var(--accent);
}

/* Article Page */
.article-container {
    margin: 40px auto;
}

.article {
    background: white;
    padding: 40px;
    border-radius: 8px;
}

.article p {
    margin-bottom: 20px;
}

.article h1 {
    font-size: 36px;
    margin-bottom: 10px;
    color: var(--primary);
}

.article h2 {
    font-size: 24px;
    margin-top: 30px;
    margin-bottom: 15px;
    color: var(--primary);
}

.article h3 {
    font-size: 18px;
    margin-top: 20px;
    margin-bottom: 10px;
}

.article blockquote {
    border-left: 4px solid var(--secondary);
    padding-left: 20px;
    margin: 20px 0;
    font-style: italic;
    color: #666;
}

.article ul, .article ol {
    margin-left: 20px;
    margin-bottom: 20px;
}

.article li {
    margin-bottom: 8px;
}

.article-footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    text-align: center;
}

.cta-box {
    background: var(--light);
    border: 2px solid var(--secondary);
    padding: 30px;
    text-align: center;
    border-radius: 8px;
    margin: 40px 0;
}

.cta-box h3 {
    color: var(--primary);
    margin-bottom: 15px;
}

/* Footer */
.site-footer {
    background: var(--primary);
    color: white;
    text-align: center;
    padding: 30px 0;
    margin-top: 60px;
}

/* Responsive */
@media (max-width: 768px) {
    .site-header .container {
        flex-direction: column;
        text-align: center;
    }

    nav a {
        margin-left: 15px;
    }

    .article {
        padding: 20px;
    }

    .article h1 {
        font-size: 24px;
    }
}
"""

        css_path = css_dir / "style.css"
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(css_content)

        logger.info(f"[site] Generated style.css")
        return css_path

    def generate_sitemap(self) -> Path:
        """Generate sitemap.xml for navigation."""
        articles = list(self.articles_dir.glob("*.html"))
        urls = [""]  # Home page

        for article_file in articles:
            urls.append(f"/articles/{article_file.stem}.html")

        sitemap_html = """<!DOCTYPE html>
<html>
<head>
    <title>Sitemap</title>
</head>
<body>
    <h1>Sitemap</h1>
    <ul>
"""
        for url in urls:
            display = url if url else "Home"
            sitemap_html += f'        <li><a href="{url}">{display}</a></li>\n'

        sitemap_html += """    </ul>
</body>
</html>"""

        sitemap_path = self.site_dir / "sitemap.html"
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(sitemap_html)

        logger.info(f"[site] Generated sitemap.html")
        return sitemap_path

    def get_site_path(self) -> Path:
        """Get path to site directory."""
        return self.site_dir
