"""Build a static presell website from presell pages."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import PresellPage

logger = logging.getLogger(__name__)


class PresellSiteBuilder:
    """Generate a complete static website with presell articles."""

    def __init__(self, site_dir: Path = Path("output/presell_site")):
        self.site_dir = site_dir
        self.articles_dir = site_dir / "articles"

    def build_site(self) -> Path:
        """Initialize site structure."""
        self.site_dir.mkdir(parents=True, exist_ok=True)
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[site] Initialized site structure at {self.site_dir}")
        return self.site_dir

    def add_article(self, page: PresellPage, article_html: str) -> Path:
        """
        Add presell page as article to site.

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

    def generate_index(self) -> Path:
        """
        Generate index.html with listing of all articles.

        Returns:
            Path to index.html
        """
        # Find all articles
        articles = list(self.articles_dir.glob("*.html"))
        article_items = []

        for article_file in sorted(articles):
            # Extract title from filename
            title = article_file.stem.replace("-", " ").title()
            slug = article_file.stem
            article_items.append(f"""
            <div class="article-card">
                <h2><a href="/articles/{slug}.html">{title}</a></h2>
                <p>Discover the latest in health and wellness.</p>
                <a href="/articles/{slug}.html" class="btn">Read More</a>
            </div>""")

        articles_html = "\n".join(article_items) if article_items else """
            <div class="article-card">
                <p>No articles yet. Create your first presell page to get started!</p>
            </div>"""

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
            {articles_html}
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

        logger.info(f"[site] Generated index.html ({len(articles)} articles)")
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
