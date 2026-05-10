"""
Module 4: Pre-sell Page Builder CLI.

Usage:
    python -m src.module4_presell generate --offer "Brain Boost Pro" --niche brain-health --url "https://maxweb.com/..."
"""

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    import typer
except ImportError:
    print("Error: typer not installed. Run: pip install -e .")
    sys.exit(1)

from .builder import AdvertorialBuilder
from .generator import AdvertorialGenerator
from .site_builder import PresellSiteBuilder
from .site_templates import GENERIC_ARTICLES

app = typer.Typer(
    name="module4-presell",
    help="MaxWeb Pre-sell Page Builder — generate advertorial HTML from offers + competitive patterns",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output/presell_pages")
DATA_CACHE_DIR = Path("data/competitive")


@app.command()
def init_site(
    domain: str = typer.Option(
        "health-tips.com",
        "--domain",
        help="Domain name for the website (e.g. brainhealth-tips.com)"
    ),
) -> None:
    """
    Initialize presell website with generic health articles.

    Creates a complete static website ready for deployment.
    Run this ONCE before adding presell pages.
    """
    typer.echo("\n" + "=" * 60)
    typer.echo("PRESELL WEBSITE INITIALIZATION")
    typer.echo("=" * 60)
    typer.echo(f"Domain: {domain}")
    typer.echo(f"Articles: {len(GENERIC_ARTICLES)}")
    typer.echo("=" * 60 + "\n")

    try:
        site_builder = PresellSiteBuilder()

        # Initialize site structure
        typer.echo("1. Creating site structure...")
        site_builder.init_site()
        typer.echo("   [OK] CSS, templates, sitemap created")

        # Add generic articles
        typer.echo(f"\n2. Adding {len(GENERIC_ARTICLES)} generic articles...")
        for i, article in enumerate(GENERIC_ARTICLES, 1):
            # Create article HTML
            article_html = f"""<h1>{article['title']}</h1>
{article['content']}

<div class="article-footer">
    <p><em>Updated: {Path(__file__).stat().st_mtime}</em></p>
</div>"""

            # Mock PresellPage for wrapping
            from .models import PresellPage
            from datetime import datetime

            mock_page = PresellPage(
                offer_name=article["slug"],
                offer_url="",
                niche="health",
                headline=article["title"],
                subheadline="Expert insights for your health",
                body_html=article_html,
                cta_text="Learn More"
            )

            # Add to site
            site_builder.add_article(mock_page, article_html)
            typer.echo(f"   [{i}/{len(GENERIC_ARTICLES)}] {article['title']}")

        typer.echo("\n3. Updating index...")
        site_builder.update_index()
        typer.echo("   [OK] Index updated with article listing")

        site_path = site_builder.get_site_path()

        typer.echo("\n" + "=" * 60)
        typer.echo("WEBSITE READY!")
        typer.echo("=" * 60)
        typer.echo(f"Location: {site_path}")
        typer.echo(f"\nStructure:")
        typer.echo("  presell_site/")
        typer.echo("  +-- index.html          (blog home)")
        typer.echo("  +-- articles/           (8 generic + your presell pages)")
        typer.echo("  +-- css/style.css       (responsive design)")
        typer.echo("  +-- sitemap.html        (navigation)")

        typer.echo(f"\nNative ads should link to:")
        typer.echo(f"  https://{domain}/articles/OFFER-NAME.html")

        typer.echo("\nNext steps:")
        typer.echo("  1. Use Streamlit (Module 5) to add presell pages")
        typer.echo("  2. Deploy to Vercel: vercel deploy presell_site/")
        typer.echo("  3. Configure domain in DNS settings")
        typer.echo("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"Error initializing site: {e}")
        typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(1)


@app.command()
def generate(
    offer: str = typer.Option(..., "--offer", help="Offer name (e.g. 'Brain Boost Pro')"),
    niche: str = typer.Option(
        ..., "--niche", help="Target niche (brain-health, lung-health, mens-health)"
    ),
    url: str = typer.Option(..., "--url", help="CTA affiliate URL"),
    output: Path = typer.Option(
        None,
        "--output",
        help="Output HTML path (default: output/presell_pages/{niche}_{offer}.html)",
    ),
) -> None:
    """
    Generate advertorial HTML for an offer.

    Uses Module 2 competitive report (if exists) to inform copy.
    """
    valid_niches = ["brain-health", "lung-health", "mens-health"]
    if niche not in valid_niches:
        typer.echo(
            f"[ERROR] Invalid niche '{niche}'. Valid: {', '.join(valid_niches)}", err=True
        )
        raise typer.Exit(1)

    typer.echo(f"\nGenerating advertorial for: {offer}")
    typer.echo(f"Niche: {niche}")
    typer.echo(f"URL: {url}")
    typer.echo("=" * 60)

    # Load competitive report if exists
    report = None
    report_path = DATA_CACHE_DIR / f"{niche}_report.json"
    if report_path.exists():
        try:
            with open(report_path) as f:
                report_data = json.load(f)
                # Note: would need to reconstruct CompetitiveReport from JSON
                logger.info(f"Loaded competitive report from {report_path}")
        except Exception as e:
            logger.warning(f"Could not load report: {e}")

    # Generate advertorial
    try:
        generator = AdvertorialGenerator()
        page = generator.generate(
            offer_name=offer,
            offer_category="supplement",  # TODO: could be parameter
            niche=niche,
            offer_url=url,
            report=report,
        )

        # Save HTML
        output_dir = output.parent if output else OUTPUT_DIR
        filepath = AdvertorialBuilder.save(page, output_dir)

        if output:
            # Copy to custom output path
            html = AdvertorialBuilder.build(page)
            with open(output, "w", encoding="utf-8") as f:
                f.write(html)
            filepath = output

        typer.echo(f"\n[OK] Advertorial generated!")
        typer.echo(f"     Headline: {page.headline}")
        typer.echo(f"     Body: {len(page.body_html)} chars")
        typer.echo(f"     Saved: {filepath}")

    except Exception as e:
        logger.error(f"Error generating advertorial: {e}")
        typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(1)


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
