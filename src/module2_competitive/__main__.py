"""
Module 2: Competitive Intelligence CLI.

Usage:
    python -m src.module2_competitive scrape --niche brain-health
    python -m src.module2_competitive scrape --niche mens-health --output report.md
    python -m src.module2_competitive analyze --niche brain-health --input ads.json
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import os
print(f"[DEBUG] ANTHROPIC_API_KEY env var exists: {'ANTHROPIC_API_KEY' in os.environ}")
print(f"[DEBUG] API key starts with: {os.environ.get('ANTHROPIC_API_KEY', 'NOT SET')[:30]}...")
use_apify = os.environ.get("USE_APIFY", "false").lower() == "true"
apify_token = os.environ.get("APIFY_API_TOKEN", "").strip()
print(f"[DEBUG] USE_APIFY: {use_apify}, APIFY_API_TOKEN set: {bool(apify_token)}")

try:
    import typer
except ImportError:
    print("Error: typer not installed. Run: pip install -e .")
    sys.exit(1)

from .analyzer import PatternAnalyzer
from .deduplicator import AdDeduplicator
from .keywords import extract_keywords
from .models import NativeAd
from .reporter import IntelReporter
from .scrapers.dailymail import DailyMailScraper
from .scrapers.news_sources import (
    HealthLineScraper,
    MedicalNewsTodayScraper,
    NPRScraper,
)

app = typer.Typer(
    name="module2-competitive",
    help="MaxWeb Competitive Intelligence — native ad pattern scraping and analysis",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output/reports")
DATA_CACHE_DIR = Path("data/competitive")


@app.command()
def scrape(
    niche: str = typer.Option(
        ..., "--niche", help="Health niche/category to scrape (e.g. 'brain-health', 'Diabetes', 'Men\'s Health')"
    ),
    output: Path = typer.Option(
        None,
        "--output",
        help="Save report to this path (default: output/reports/competitive_intel_DATE_NICHE.md)",
    ),
    skip_analysis: bool = typer.Option(
        False,
        "--skip-analysis",
        help="Scrape only, skip Claude API analysis (save for later)",
    ),
    sources: str = typer.Option(
        "healthline,medicalnewstoday,npr,dailymail",
        "--sources",
        help="Comma-separated scrape sources (healthline, medicalnewstoday, npr, dailymail recommended)",
    ),
    keywords: str = typer.Option(
        None,
        "--keywords",
        help="Comma-separated search keywords (auto-extracted from niche if not set)",
    ),
) -> None:
    """
    Scrape native ads for a niche, analyze with Claude, generate Markdown report.

    Examples:
        python -m src.module2_competitive scrape --niche brain-health
        python -m src.module2_competitive scrape --niche "Joint Supplement"
    """
    source_list = [s.strip() for s in sources.split(",")]
    cache_path = DATA_CACHE_DIR / f"{niche}_ads.json"

    # Use provided keywords or extract from niche
    if keywords:
        keywords_list = [k.strip() for k in keywords.split(",")]
    else:
        keywords_list = extract_keywords(niche)

    typer.echo(f"\nScraping native ads for niche: {niche}")
    typer.echo(f"Keywords: {', '.join(keywords_list)}")
    typer.echo(f"Sources: {', '.join(source_list)}")
    typer.echo("=" * 60)

    # Clear cache for fresh scrape
    if cache_path.exists():
        cache_path.unlink()
        typer.echo(f"  Cleared old cache")

    all_ads: list[NativeAd] = []
    deduplicator = AdDeduplicator(cache_path=cache_path)

    for source in source_list:
        typer.echo(f"  Scraping {source}...")
        try:
            scraper = None
            if source == "healthline":
                scraper = HealthLineScraper(niche)
            elif source == "medicalnewstoday":
                scraper = MedicalNewsTodayScraper(niche)
            elif source == "npr":
                scraper = NPRScraper(niche)
            elif source == "dailymail":
                scraper = DailyMailScraper(niche=niche)
            else:
                typer.echo(f"[WARN] Unknown source '{source}', skipping", err=True)
                continue

            if scraper:
                ads = scraper.scrape()
                unique_ads = deduplicator.deduplicate(ads)
                all_ads.extend(unique_ads)
                typer.echo(f"  -> {len(unique_ads)} unique from {source}")
        except Exception as e:
            logger.error(f"Error scraping {source}: {e}")
            typer.echo(f"[ERROR] {source}: {e}", err=True)

    typer.echo(f"\nTotal unique ads collected: {len(all_ads)}")

    if len(all_ads) < 10:
        typer.echo(
            "[WARN] Fewer than 10 ads collected — analysis may be thin. "
            "Try running again or check scraper logs.",
            err=True,
        )

    deduplicator.save_cache(all_ads)

    if skip_analysis:
        typer.echo("[OK] Scrape-only mode. Skipping Claude analysis.")
        return

    typer.echo("\nSending ads to Claude for pattern analysis...")
    analyzer = PatternAnalyzer()
    report = analyzer.analyze(all_ads, niche)

    output_dir = output.parent if output else OUTPUT_DIR
    report_path = IntelReporter.save(report, output_dir)
    if output:
        report_path = output
        IntelReporter.save(report, output.parent)

    typer.echo(f"\n[OK] Report saved to: {report_path}")
    typer.echo(f"     Ads analyzed: {report.ads_analyzed}")
    if report.top_hooks:
        typer.echo(f"     Top hooks: {', '.join(p.value for p in report.top_hooks[:3])}")
    typer.echo(f"     Saturation warnings: {len(report.saturation_warnings)}")


@app.command()
def analyze(
    niche: str = typer.Option(..., "--niche", help="Niche slug"),
    input_file: Path = typer.Option(
        None, "--input", help="JSON file of previously scraped ads"
    ),
    output: Path = typer.Option(None, "--output", help="Output Markdown path"),
) -> None:
    """
    Run Claude analysis on previously scraped ads (no re-scraping).

    Examples:
        python -m src.module2_competitive analyze --niche brain-health
    """
    cache_path = input_file or DATA_CACHE_DIR / f"{niche}_ads.json"
    if not cache_path.exists():
        typer.echo(f"[ERROR] No cached ads found at {cache_path}. Run scrape first.", err=True)
        raise typer.Exit(1)

    with open(cache_path, encoding="utf-8") as f:
        raw = json.load(f)
    ads = [NativeAd(**item) for item in raw]

    typer.echo(f"Loaded {len(ads)} cached ads for {niche}")
    analyzer = PatternAnalyzer()
    report = analyzer.analyze(ads, niche)

    output_dir = output.parent if output else OUTPUT_DIR
    report_path = IntelReporter.save(report, output_dir)
    typer.echo(f"[OK] Report saved to: {report_path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
