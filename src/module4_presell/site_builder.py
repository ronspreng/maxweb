"""Build a static presell website from presell pages."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

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

    def add_article(self, page: PresellPage, article_html: str, folder: str = "articles") -> Path:
        """
        Add presell page as article to site.
        Saves article and optionally updates index.html.

        Args:
            page: PresellPage model
            article_html: Generated HTML content
            folder: "articles" (editorial, on index) or "presell-ads" (advertorial, not on index)

        Returns:
            Path to saved article
        """
        # Determine target directory based on folder type
        if folder == "presell-ads":
            target_dir = self.site_dir / "presell-ads"
        else:
            target_dir = self.articles_dir

        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate article filename from H1 headline (if available), fallback to offer_name
        slug = None
        match = re.search(r"<h1>\s*([^<]+?)\s*</h1>", article_html, re.IGNORECASE)
        if match:
            headline = match.group(1).strip()
            slug = headline.lower().replace(" ", "-").replace("'", "").replace(".", "").replace(":", "-")

        if not slug:
            slug = page.offer_name.lower().replace(" ", "-").replace("'", "").replace(":", "-")

        # Ensure unique filename—add -2, -3, etc if exists
        base_slug = slug
        counter = 2
        filename = f"{slug}.html"
        filepath = target_dir / filename

        while filepath.exists():
            slug = f"{base_slug}-{counter}"
            filename = f"{slug}.html"
            filepath = target_dir / filename
            counter += 1
            logger.info(f"[site] Filename {base_slug}.html exists, trying {filename}")

        # Wrap in article template with navigation
        html = self._wrap_article(page, article_html, slug)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"[site] Added {folder} article: {filename}")

        # Update index listing only for editorial articles, not for presell ads
        if folder == "articles":
            self.update_index()
        else:
            logger.info(f"[site] Skipped index update for presell ad: {filename}")

        return filepath

    def _wrap_article(self, page: PresellPage, body_html: str, slug: str) -> str:
        """Wrap presell page in article template with navigation."""
        pub_date = page.generated_at.strftime("%Y-%m-%d") if page.generated_at else ""

        # Extract only the body content if full HTML document was passed
        content = body_html
        if "<!DOCTYPE" in content or "<html" in content.lower():
            # Extract content between <body> tags
            match = re.search(r"<body[^>]*>(.*?)</body>", content, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()

        # Keep only the FIRST h1, remove all subsequent h1 tags
        first_h1 = re.search(r'<h1[^>]*>.*?</h1>', content, re.IGNORECASE | re.DOTALL)
        if first_h1:
            # Keep everything up to and including the first h1
            before_h1 = content[:first_h1.end()]
            after_h1 = content[first_h1.end():]
            # Remove all h1 tags from the rest
            after_h1 = re.sub(r'<h1[^>]*>.*?</h1>', '', after_h1, flags=re.IGNORECASE | re.DOTALL)
            content = before_h1 + after_h1

        # Clean up opening <p><em>...</em></p> lines
        content = re.sub(r'^\s*<p><em>.*?</em></p>\s*', '', content, flags=re.IGNORECASE)
        content = content.lstrip()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="article:published_time" content="{pub_date}">
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
            {content}
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
        Regenerate index.html with current article listing.
        Rebuilds from scratch to avoid duplication.
        Articles are sorted by publication date (newest first).

        Returns:
            Path to index.html
        """
        from datetime import datetime as dt

        # Find all articles with their dates
        articles = list(self.articles_dir.glob("*.html"))
        article_dates = []

        for article_file in articles:
            slug = article_file.stem
            pub_date_str = ""
            try:
                with open(article_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Try to extract date from meta tag first
                    match = re.search(r'<meta name="article:published_time" content="([^"]+)"', content)
                    if match:
                        pub_date_str = match.group(1)
                    else:
                        # Fallback to file modification time
                        mod_time = article_file.stat().st_mtime
                        pub_date_str = dt.fromtimestamp(mod_time).strftime("%Y-%m-%d")
                # Parse date for sorting
                pub_date = dt.strptime(pub_date_str, "%Y-%m-%d")
                article_dates.append((pub_date, article_file))
            except Exception as e:
                logger.warning(f"Could not extract date from {article_file}: {e}")
                # Use modification time as fallback
                mod_time = article_file.stat().st_mtime
                pub_date = dt.fromtimestamp(mod_time)
                article_dates.append((pub_date, article_file))

        # Sort by date, newest first
        article_dates.sort(key=lambda x: x[0], reverse=True)

        article_items = []

        for pub_date_obj, article_file in article_dates:
            slug = article_file.stem
            pub_date_str = pub_date_obj.strftime("%Y-%m-%d")

            # Extract title from HTML
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
            date_html = f'<span>{pub_date_str}</span>'
            slug_encoded = quote(slug, safe="-")
            article_items.append(f"""                <article class="article-card">
                    <div class="article-card-content">
                        <div class="article-card-meta">
                            <span>{category}</span>
                            {date_html}
                        </div>
                        <h3><a href="/articles/{slug_encoded}.html">{title}</a></h3>
                        <p>Discover the latest in health and wellness insights and practical strategies.</p>
                        <a href="/articles/{slug_encoded}.html" class="btn">Read More</a>
                    </div>
                </article>""")

        articles_html = "\n".join(article_items) if article_items else """            <div class="article-card">
                <p>No articles yet. Create your first presell page to get started!</p>
            </div>"""

        # Rebuild index from scratch to avoid duplication issues
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
{articles_html}
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

        # Write back
        index_path = self.site_dir / "index.html"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_html)

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

    def list_articles(self, folder: str = "articles") -> list:
        """
        List all articles in a folder with their titles.

        Args:
            folder: "articles" (editorial) or "presell-ads" (advertorials)

        Returns:
            List of dicts: [{"filename": "slug.html", "title": "...", "folder": "..."}]
        """
        target_dir = self.site_dir / folder
        if not target_dir.exists():
            return []

        articles = []
        for article_file in sorted(target_dir.glob("*.html")):
            title = article_file.stem.replace("-", " ").title()
            try:
                with open(article_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    match = re.search(r"<h1>\s*([^<]+?)\s*</h1>", content, re.IGNORECASE)
                    if match:
                        title = match.group(1).strip()
            except Exception as e:
                logger.warning(f"Could not extract title from {article_file}: {e}")

            articles.append({
                "filename": article_file.name,
                "title": title,
                "folder": folder
            })

        return articles

    def delete_article(self, filename: str, folder: str = "presell-ads", auto_push: bool = True) -> bool:
        """
        Delete an article and optionally commit+push to GitHub.

        Args:
            filename: article filename (e.g. "my-article.html")
            folder: "articles" or "presell-ads"
            auto_push: whether to git commit and push

        Returns:
            True if successful, False otherwise
        """
        try:
            target_dir = self.site_dir / folder
            filepath = target_dir / filename

            logger.info(f"[site] Attempting to delete: {filepath} (exists: {filepath.exists()})")

            if not filepath.exists():
                logger.warning(f"[site] Article not found: {filepath}")
                return False

            # Delete file
            filepath.unlink()
            logger.info(f"[site] File deleted from disk: {filepath}")

            # Update index if editorial article
            if folder == "articles":
                self.update_index()
                logger.info(f"[site] Updated index.html after deletion")

            # Commit and push if requested
            if auto_push:
                try:
                    import subprocess
                    import os

                    # Get current working directory
                    cwd = os.getcwd()
                    logger.info(f"[site] Git CWD: {cwd}")

                    # Try to compute relative path safely
                    try:
                        folder_path = str(target_dir.relative_to(Path.cwd()))
                        logger.info(f"[site] Relative folder path: {folder_path}")
                    except ValueError:
                        # If relative_to fails, use absolute path
                        folder_path = str(target_dir)
                        logger.warning(f"[site] Using absolute path: {folder_path}")

                    # Stage changes
                    logger.info(f"[site] Running: git add {folder_path}")
                    result = subprocess.run(
                        ["git", "add", folder_path],
                        capture_output=True,
                        cwd=".",
                    )
                    logger.info(f"[site] git add result: {result.returncode}, stderr: {result.stderr.decode()}")

                    # Also stage index.html if articles folder
                    if folder == "articles":
                        logger.info(f"[site] Running: git add output/presell_site/index.html")
                        result = subprocess.run(
                            ["git", "add", "output/presell_site/index.html"],
                            capture_output=True,
                            cwd=".",
                        )
                        logger.info(f"[site] git add index result: {result.returncode}")

                    # Commit
                    logger.info(f"[site] Running: git commit -m 'Delete: {filename} from {folder}'")
                    result = subprocess.run(
                        ["git", "commit", "-m", f"Delete: {filename} from {folder}"],
                        capture_output=True,
                        cwd=".",
                    )
                    logger.info(f"[site] git commit result: {result.returncode}, stdout: {result.stdout.decode()}, stderr: {result.stderr.decode()}")

                    # Push
                    logger.info(f"[site] Running: git push origin master")
                    result = subprocess.run(
                        ["git", "push", "origin", "master"],
                        capture_output=True,
                        cwd=".",
                    )
                    logger.info(f"[site] git push result: {result.returncode}")

                    if result.returncode != 0:
                        logger.error(f"[site] Push failed: {result.stderr.decode()}")
                        return False

                    logger.info(f"[site] Pushed deletion to GitHub: {filename}")
                except Exception as e:
                    logger.error(f"[site] Git error: {e}", exc_info=True)
                    return False

            return True

        except Exception as e:
            logger.error(f"[site] Delete error: {e}", exc_info=True)
            return False
