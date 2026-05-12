"""CLI for campaign analysis."""
import sys
from pathlib import Path
from .scraper import ClickHubScraper
from .analyzer import CampaignAnalyzer
from .reporter import CampaignReporter

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.module5_feedback <campaign_name> [days]")
        sys.exit(1)

    campaign_name = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    # Scrape ClickHub
    scraper = ClickHubScraper()
    if not scraper.login():
        print("Failed to login to ClickHub")
        sys.exit(1)

    analysis = scraper.analyze_campaign(campaign_name, days=days)
    if not analysis:
        print(f"Campaign '{campaign_name}' not found")
        sys.exit(1)

    # Analyze
    analyzer = CampaignAnalyzer(roi_target=20.0)
    recommendations = analyzer.analyze(analysis)

    # Report
    report = CampaignReporter.generate_markdown(analysis, recommendations)
    print(report)

    # Save report
    output_dir = Path("output/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / f"campaign_analysis_{campaign_name}_{days}d.md"
    report_file.write_text(report)
    print(f"\nReport saved: {report_file}")
