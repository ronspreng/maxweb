"""Generate all 15 articles with conversion-optimized templates."""
import os
from pathlib import Path
from src.module4_presell.site_templates import GENERIC_ARTICLES

def generate_article_html(article: dict, all_articles: list) -> str:
    """Generate conversion-optimized HTML for an article."""

    # Remove duplicate h1 from content (already in page title)
    content = article["content"]
    # Find and remove the first <h1>...</h1> block
    h1_start = content.find("<h1>")
    if h1_start != -1:
        h1_end = content.find("</h1>", h1_start) + 5
        content = content[:h1_start] + content[h1_end:]
        content = content.lstrip()

    # Get related articles (first 3 others)
    related = [a for a in all_articles if a["slug"] != article["slug"]][:3]
    related_html = ""
    if related:
        related_html = '<div class="related-articles"><h3>Related Articles</h3><div class="related-grid">'
        for r in related:
            related_html += f'''
            <div class="related-card">
                <h4>{r["title"].split(":")[0]}</h4>
                <p>Discover evidence-based insights on {r["title"].lower()}.</p>
                <a href="/articles/{r["slug"]}.html">Read More →</a>
            </div>
            '''
        related_html += '</div></div>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article["title"]} - Health & Wellness</title>
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

    <main class="container article-container">
        <article class="article">
            <h1>{article["title"]}</h1>

            <!-- Article Meta Info -->
            <div class="article-meta">
                <div class="article-meta-item">
                    <strong>Published:</strong> May 2026
                </div>
                <div class="article-meta-item">
                    <strong>Updated:</strong> May 10, 2026
                </div>
                <div class="article-meta-item">
                    <strong>Read Time:</strong> 6 minutes
                </div>
                <div class="article-meta-item">
                    <strong>Category:</strong> Brain Health & Wellness
                </div>
            </div>

            <!-- Trust Badges -->
            <div class="trust-badges">
                <span class="badge">Evidence-Based Research</span>
                <span class="badge">Expert Reviewed</span>
                <span class="badge">Medically Accurate</span>
                <span class="badge">Updated 2026</span>
            </div>

            <!-- Main Content -->
            {content}

            <!-- CTA Box 1 -->
            <div class="cta-box">
                <h3>Ready to Take Action?</h3>
                <p>Thousands of people have improved their health and wellness. Discover the science-backed strategies that work.</p>
                <a href="#" class="cta-button">Explore Our Wellness System →</a>
            </div>

            <!-- Author Bio -->
            <div class="author-bio">
                <strong>Written by: Health & Wellness Team</strong>
                <p>Our team of health experts and researchers are dedicated to providing evidence-based information to help you optimize your health. All content is reviewed by medical professionals and supported by scientific research.</p>
            </div>

            <!-- Email Signup -->
            <div class="email-signup">
                <h4>Get Health Tips Delivered to Your Inbox</h4>
                <p>Join thousands of people receiving science-backed wellness insights every week.</p>
                <form class="email-form" onsubmit="return false;">
                    <input type="email" placeholder="Enter your email" required>
                    <button type="submit">Subscribe</button>
                </form>
                <p class="email-disclaimer">We respect your privacy. Unsubscribe anytime.</p>
            </div>

            <!-- Related Articles -->
            {related_html}

            <!-- CTA Box 2 -->
            <div class="cta-box">
                <h3>Want to Learn More?</h3>
                <p>Our comprehensive wellness guide covers everything you need to optimize your health and achieve lasting results.</p>
                <a href="#" class="cta-button">Explore Our Complete System →</a>
            </div>

            <div class="article-footer">
                <p>Disclaimer: This article is for educational purposes only. Always consult with a healthcare professional before making health decisions. <a href="/disclaimer.html">Read our full disclaimer</a>.</p>
            </div>
        </article>
    </main>

    <footer class="site-footer">
        <div class="container">
            <p>&copy; 2026 Health & Wellness. All rights reserved. | <a href="/disclaimer.html">Disclaimer</a> | <a href="/privacy-policy.html">Privacy</a> | <a href="/contact.html">Contact</a></p>
        </div>
    </footer>
</body>
</html>'''

    return html

def main():
    """Generate all articles."""
    output_dir = Path("output/presell_site/articles")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating {len(GENERIC_ARTICLES)} conversion-optimized articles...")
    print("=" * 60)

    for article in GENERIC_ARTICLES:
        html = generate_article_html(article, GENERIC_ARTICLES)
        filepath = output_dir / f"{article['slug']}.html"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"[OK] {filepath.name}")

    print("=" * 60)
    print(f"\n[OK] All {len(GENERIC_ARTICLES)} articles generated!")
    print(f"Location: {output_dir}")
    print("\nEach article includes:")
    print("  - Meta info (publish date, update date, read time)")
    print("  - Trust badges (Evidence-Based, Expert Reviewed, etc.)")
    print("  - 2x CTA boxes with affiliate link placeholders")
    print("  - Author bio")
    print("  - Email signup")
    print("  - Related articles (auto-linked)")
    print("  - Compliance footer")
    print("\nNext: Replace '#' in CTA links with your affiliate URLs!")

if __name__ == "__main__":
    main()
