"""
Module 1: Offer Intelligence CLI.

Usage:
    python -m src.module1_offers rank --budget 1500 [--input offers.csv]
"""

import json
import logging
import sys
from pathlib import Path

try:
    import typer
except ImportError:
    print("Error: typer not installed. Run: pip install -e .")
    sys.exit(1)

from .importer import CSVImporter
from .models import Offer
from .ranker import OfferRanker

app = typer.Typer(
    name="module1-offers",
    help="MaxWeb Offer Intelligence & Ranking",
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@app.command()
def rank(
    budget: float = typer.Option(
        1500.0, help="Campaign budget in USD (for context)"
    ),
    input_csv: Path = typer.Option(
        None,
        "--input",
        help="Path to CSV file with offers. If not provided, uses test data.",
    ),
    output_json: Path = typer.Option(
        None,
        "--output-json",
        help="Save results as JSON to this file",
    ),
    output_markdown: Path = typer.Option(
        None,
        "--output-md",
        help="Save results as Markdown to this file",
    ),
):
    """
    Rank MaxWeb offers by fit-score.

    Examples:
        python -m src.module1_offers rank --budget 1500
        python -m src.module1_offers rank --input data/offers.csv --output-md output/ranking.md
    """

    # Load offers
    if input_csv and input_csv.exists():
        logger.info(f"Loading offers from {input_csv}")
        offers = CSVImporter.import_csv(input_csv)
    else:
        logger.info("No CSV provided, using test data")
        offers = _load_test_offers()

    if not offers:
        typer.echo("No offers to rank.", err=True)
        raise typer.Exit(1)

    # Rank
    ranker = OfferRanker(budget_usd=budget)
    ranked = ranker.rank_offers(offers)

    # Display
    _print_ranked_table(ranked)

    # Save if requested
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w") as f:
            json.dump(
                [
                    {
                        "rank": r.rank,
                        "offer": r.offer.model_dump(),
                        "score": r.score.model_dump(),
                    }
                    for r in ranked
                ],
                f,
                indent=2,
                default=str,
            )
        typer.echo(f"[OK] Saved JSON to {output_json}")

    if output_markdown:
        output_markdown.parent.mkdir(parents=True, exist_ok=True)
        with open(output_markdown, "w") as f:
            f.write(_ranked_to_markdown(ranked, budget))
        typer.echo(f"[OK] Saved Markdown to {output_markdown}")


def _print_ranked_table(ranked: list) -> None:
    """Print ranked offers as a table."""
    typer.echo("")
    typer.echo("=" * 100)
    typer.echo(
        f"{'Rank':<6} {'Offer':<30} {'Payout':<10} {'EPC':<8} {'Refund':<10} {'Score':<8}"
    )
    typer.echo("=" * 100)

    for item in ranked[:5]:  # Show top 5
        offer = item.offer
        score = item.score
        typer.echo(
            f"{item.rank:<6} {offer.name[:29]:<30} "
            f"${offer.payout:<9.0f} ${offer.epc:<7.2f} "
            f"{offer.refund_rate:<9.1f}% {score.overall_score:<8.3f}"
        )

    typer.echo("=" * 100)
    typer.echo(f"Total offers ranked: {len(ranked)}\n")


def _ranked_to_markdown(ranked: list, budget: float) -> str:
    """Convert ranked offers to Markdown report."""
    lines = [
        "# Offer Ranking Report",
        f"\n**Budget:** ${budget:,.0f}",
        f"**Generated:** {Path.cwd()}",
        f"**Total Offers:** {len(ranked)}\n",
        "## Top 5 Ranked Offers\n",
    ]

    for item in ranked[:5]:
        offer = item.offer
        score = item.score
        lines.extend(
            [
                f"### #{item.rank} - {offer.name}",
                f"- **Overall Score:** {score.overall_score:.3f}",
                f"- **Payout:** ${offer.payout:.0f}",
                f"- **EPC:** ${offer.epc:.2f}",
                f"- **Refund Rate:** {offer.refund_rate:.1f}%",
                f"- **Competition:** {offer.competition}",
                f"- **Age:** {offer.age_days} days",
                f"- **Geo:** {', '.join(offer.geo)}",
                f"- **Rationale:** {score.rationale}",
                "",
            ]
        )

    return "\n".join(lines)


def _load_test_offers() -> list[Offer]:
    """Load test data for development."""
    return [
        Offer(
            id="gluco-savior-001",
            name="GlucoSavior Blood Sugar Support",
            category="nutra_health",
            payout=120.0,
            epc=1.80,
            refund_rate=12.5,
            competition="medium",
            age_days=210,
            geo=["US"],
        ),
        Offer(
            id="cardio-boost-002",
            name="CardioBoost Heart Health",
            category="nutra_health",
            payout=95.0,
            epc=1.20,
            refund_rate=18.0,
            competition="high",
            age_days=450,
            geo=["US"],
        ),
        Offer(
            id="joint-flex-003",
            name="JointFlex Mobility Support",
            category="nutra_health",
            payout=85.0,
            epc=1.50,
            refund_rate=8.0,
            competition="low",
            age_days=90,
            geo=["US"],
        ),
        Offer(
            id="memory-pro-004",
            name="MemoryPro Cognitive Enhancement",
            category="nutra_health",
            payout=140.0,
            epc=2.10,
            refund_rate=22.0,
            competition="high",
            age_days=365,
            geo=["US"],
        ),
        Offer(
            id="sleep-zen-005",
            name="SleepZen Natural Sleep Aid",
            category="nutra_health",
            payout=75.0,
            epc=0.90,
            refund_rate=35.0,
            competition="medium",
            age_days=30,
            geo=["US"],
        ),
        Offer(
            id="vision-clear-006",
            name="VisionClear Eye Health",
            category="nutra_health",
            payout=110.0,
            epc=1.65,
            refund_rate=14.0,
            competition="low",
            age_days=220,
            geo=["US"],
        ),
        Offer(
            id="energy-surge-007",
            name="EnergySurge Vitality Booster",
            category="nutra_health",
            payout=65.0,
            epc=0.75,
            refund_rate=28.0,
            competition="high",
            age_days=600,
            geo=["US"],
        ),
        Offer(
            id="skin-renew-008",
            name="SkinRenew Anti-Aging Formula",
            category="beauty_health",
            payout=130.0,
            epc=1.95,
            refund_rate=16.0,
            competition="medium",
            age_days=180,
            geo=["US"],
        ),
        Offer(
            id="weight-trim-009",
            name="WeightTrim Appetite Support",
            category="nutra_health",
            payout=105.0,
            epc=1.40,
            refund_rate=31.0,
            competition="high",
            age_days=120,
            geo=["US"],
        ),
        Offer(
            id="bone-strong-010",
            name="BoneStrong Skeletal Support",
            category="nutra_health",
            payout=100.0,
            epc=1.55,
            refund_rate=10.0,
            competition="low",
            age_days=270,
            geo=["US"],
        ),
    ]


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
