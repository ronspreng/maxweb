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
