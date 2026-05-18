"""Daily Module 5 cron: scrape ClickHub, analyze, write daily report.

Loopt over alle ClickHub-campagnes met traffic in de laatste N dagen,
analyseert kill/scale-kandidaten, en schrijft een geaggregeerd dagrapport
naar `data/daily_reports/YYYY-MM-DD.md`.

Optioneel: post een korte samenvatting naar Discord webhook als
`DISCORD_WEBHOOK_URL` in `.env` staat.

Gebruik:
    python scripts/daily_report.py                # last 1 day (default)
    python scripts/daily_report.py --days 7       # last 7 days
    python scripts/daily_report.py --campaigns BMK,FluxoMax  # alleen deze

Voor automatische dagelijkse uitvoering: gebruik Windows Task Scheduler
met scripts/run_daily_report.ps1 als trigger.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=True)

from src.module5_feedback.scraper import ClickHubScraper  # noqa: E402
from src.module5_feedback.analyzer import CampaignAnalyzer  # noqa: E402
from src.module5_feedback.reporter import CampaignReporter  # noqa: E402

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
REPORTS_DIR = PROJECT_ROOT / "data" / "daily_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"daily_report_{datetime.now():%Y-%m-%d}.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def post_to_discord(webhook_url: str, content: str) -> None:
    """Stuur samenvatting naar Discord. Negeert fouten."""
    try:
        import requests

        # Discord limit: 2000 chars per message
        if len(content) > 1900:
            content = content[:1900] + "\n…(truncated, zie volledig rapport)"
        r = requests.post(webhook_url, json={"content": content}, timeout=10)
        if r.status_code >= 400:
            logger.warning(f"Discord webhook returned {r.status_code}: {r.text[:200]}")
    except Exception as exc:
        logger.warning(f"Discord post faalde: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Daily Module 5 rapport")
    parser.add_argument("--days", type=int, default=1, help="Periode in dagen (default 1)")
    parser.add_argument(
        "--campaigns",
        type=str,
        default="",
        help="Comma-separated campaign-namen (default: alle met traffic)",
    )
    parser.add_argument(
        "--no-discord", action="store_true", help="Skip Discord webhook ook als hij geset is"
    )
    args = parser.parse_args()

    logger.info(f"=== Daily report start (last {args.days} day{'s' if args.days != 1 else ''}) ===")

    # 1. ClickHub login
    scraper = ClickHubScraper()
    if not scraper.login():
        logger.error("ClickHub login mislukt — check CLICKHUB_EMAIL/PASSWORD in .env")
        sys.exit(1)

    # 2. Fetch all campaigns
    try:
        all_campaigns = scraper.fetch_campaigns()
    except Exception as exc:
        logger.error(f"fetch_campaigns failed: {exc}")
        sys.exit(1)

    if args.campaigns:
        filter_names = {n.strip().lower() for n in args.campaigns.split(",") if n.strip()}
        all_campaigns = [c for c in all_campaigns if c.get("name", "").lower() in filter_names]
        logger.info(f"Filter: {len(all_campaigns)} campagnes na naam-filter")

    # 3. Analyseer per campagne
    analyzer = CampaignAnalyzer(roi_target=20.0)
    summaries = []
    all_recs_by_action = {"kill": [], "scale": [], "optimize": [], "maintain": []}

    for c in all_campaigns:
        name = c.get("name", "")
        if not name:
            continue
        # Skip campagnes zonder recente traffic — bespaart API-calls
        try:
            recent_visits = float(str(c.get("visits", 0)).replace(",", "")) or 0
        except (ValueError, TypeError):
            recent_visits = 0
        if recent_visits < 10:
            logger.info(f"  skip '{name}': geen significante traffic ({recent_visits} visits)")
            continue

        logger.info(f"Analyseer: {name}")
        try:
            analysis = scraper.analyze_campaign(name, days=args.days)
        except Exception as exc:
            logger.warning(f"  analyze faalde voor {name}: {exc}")
            continue

        if not analysis:
            continue

        recs = analyzer.analyze(analysis)

        # Aggregeer per action-type
        for r in recs:
            if r.action in all_recs_by_action:
                all_recs_by_action[r.action].append(
                    {"campaign": name, "sub_id": r.sub_id, "value": r.current_value, "reason": r.reason}
                )

        # Korte campagne-samenvatting
        summaries.append({
            "name": name,
            "visits": analysis.total_visits,
            "conversions": analysis.total_conversions,
            "revenue": analysis.total_revenue,
            "cost": analysis.total_cost,
            "profit": analysis.total_profit,
            "roi": analysis.overall_roi,
            "n_kill": sum(1 for r in recs if r.action == "kill"),
            "n_scale": sum(1 for r in recs if r.action == "scale"),
            "n_optimize": sum(1 for r in recs if r.action == "optimize"),
        })

    # 4. Bouw daily report markdown
    today = datetime.now().strftime("%Y-%m-%d")
    md_lines = [
        f"# Daily Campaign Report — {today}",
        "",
        f"_Periode: last {args.days} day(s). Gegenereerd om {datetime.now():%H:%M:%S}._",
        "",
        "## 🚨 Action items",
        "",
    ]

    if all_recs_by_action["kill"]:
        md_lines.append(f"### ❌ KILL ({len(all_recs_by_action['kill'])} sub-IDs)")
        md_lines.append("")
        md_lines.append("| Campaign | Sub-ID | ROI | Reason |")
        md_lines.append("|---|---|---|---|")
        for r in all_recs_by_action["kill"][:15]:
            md_lines.append(f"| {r['campaign']} | `{r['sub_id']}` | {r['value']:.1f}% | {r['reason']} |")
        md_lines.append("")

    if all_recs_by_action["scale"]:
        md_lines.append(f"### 🚀 SCALE ({len(all_recs_by_action['scale'])} sub-IDs)")
        md_lines.append("")
        md_lines.append("| Campaign | Sub-ID | ROI | Reason |")
        md_lines.append("|---|---|---|---|")
        for r in all_recs_by_action["scale"][:15]:
            md_lines.append(f"| {r['campaign']} | `{r['sub_id']}` | {r['value']:.1f}% | {r['reason']} |")
        md_lines.append("")

    if all_recs_by_action["optimize"]:
        md_lines.append(f"### 🛠️ OPTIMIZE ({len(all_recs_by_action['optimize'])} sub-IDs)")
        md_lines.append("")
        md_lines.append("Promising sub-IDs (ROI 0-20%) — test headlines/landing pages.")
        md_lines.append("")

    if not any([all_recs_by_action["kill"], all_recs_by_action["scale"]]):
        md_lines.append("_Geen kritieke kill/scale-signalen vandaag._")
        md_lines.append("")

    # 5. Campagne-overzicht
    md_lines.append("## 📊 Campaign overview")
    md_lines.append("")
    if summaries:
        md_lines.append("| Campaign | Visits | Conv | Rev | Cost | Profit | ROI |")
        md_lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for s in sorted(summaries, key=lambda x: x["profit"], reverse=True):
            profit_marker = "💰" if s["profit"] > 0 else "🔴" if s["profit"] < -5 else ""
            md_lines.append(
                f"| {s['name']} | {s['visits']:,} | {s['conversions']} | "
                f"${s['revenue']:.2f} | ${s['cost']:.2f} | {profit_marker} ${s['profit']:.2f} | "
                f"{s['roi']:.1f}% |"
            )
        md_lines.append("")

        # Totaal
        total_rev = sum(s["revenue"] for s in summaries)
        total_cost = sum(s["cost"] for s in summaries)
        total_profit = total_rev - total_cost
        total_roi = ((total_rev - total_cost) / total_cost * 100) if total_cost > 0 else 0
        md_lines.append("### Totaal")
        md_lines.append(f"- **Revenue**: ${total_rev:.2f}")
        md_lines.append(f"- **Cost**: ${total_cost:.2f}")
        md_lines.append(f"- **Profit**: ${total_profit:.2f}")
        md_lines.append(f"- **ROI**: {total_roi:.1f}%")
        md_lines.append("")
    else:
        md_lines.append("_Geen campagnes met data deze periode._")
        md_lines.append("")

    # 6. Schrijf naar disk
    report_path = REPORTS_DIR / f"{today}.md"
    report_path.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info(f"✓ Report saved: {report_path}")

    # 7. Optioneel Discord
    discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if discord_url and not args.no_discord:
        n_kill = len(all_recs_by_action["kill"])
        n_scale = len(all_recs_by_action["scale"])
        total_profit = sum(s["profit"] for s in summaries) if summaries else 0
        summary = (
            f"**📊 Daily Campaign Report — {today}**\n"
            f"• {len(summaries)} active campaigns\n"
            f"• 🚀 Scale: {n_scale} · ❌ Kill: {n_kill}\n"
            f"• Profit (24h): ${total_profit:.2f}\n"
            f"_Full report: `data/daily_reports/{today}.md`_"
        )
        post_to_discord(discord_url, summary)
        logger.info("✓ Discord notification sent")

    logger.info("=== Daily report done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
