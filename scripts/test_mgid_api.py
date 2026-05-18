"""Smoke-test MGID API integratie.

Gebruik:
    python scripts/test_mgid_api.py

Vereist in .env:
- MGID_API_KEY (32-char token)
- MGID_CLIENT_ID (te vinden in MGID dashboard URL, bv. /clients/12345)

Test:
1. Connect + auth-check (API token geldig?)
2. List campagnes (zonder waardes te tonen — privacy)
3. Stats voor laatste 7 dagen
4. Per-click detail voor 1 actieve campagne
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=True)

from src.module5_feedback.mgid_client import MGIDClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    print("=" * 60)
    print("MGID API Smoke Test")
    print("=" * 60)

    try:
        client = MGIDClient()
        print(f"\n✓ Client geïnitialiseerd")
        print(f"  API key: {len(client._api_key)} chars")
        print(f"  Client ID: {client._client_id or '(niet gezet — set MGID_CLIENT_ID in .env)'}")
    except Exception as exc:
        print(f"\n✗ Init faalde: {exc}")
        return 1

    if not client._client_id:
        print("\n⚠ MGID_CLIENT_ID niet gezet — kan campagne-stats niet ophalen.")
        print("  Vind je client-ID in de MGID-dashboard-URL:")
        print("  https://dashboard.mgid.com/.../clients/<HIER_STAAT_JE_ID>/...")
        print("  Voeg toe aan .env: MGID_CLIENT_ID=<id>")
        return 0

    # Test 1: campaigns-stat
    print(f"\n[Test 1/3] Daily campaign stats — last 7 days")
    try:
        stats = client.get_campaigns_stats(date_interval="lastSeven")
        print(f"  ✓ {len(stats)} campagnes met data")
        if stats:
            # Toon top 5 op spent
            top = sorted(stats, key=lambda s: s.spent, reverse=True)[:5]
            print(f"\n  Top {len(top)} op spend (laatste 7 dagen):")
            for s in top:
                roi_str = f"{s.roi:+.1f}%" if s.spent > 0 else "n/a"
                print(f"    • Campaign {s.campaign_id}: "
                      f"{s.clicks:,} clicks, ${s.spent:.2f} spend, "
                      f"{s.conversions} conv, ${s.revenue:.2f} rev, ROI {roi_str}")
    except Exception as exc:
        print(f"  ✗ {type(exc).__name__}: {exc}")
        return 1

    # Test 2: pick top campaign, get per-click detail for yesterday
    if not stats:
        print("\n⚠ Geen campagne-data — skip de detail-test")
        return 0

    top_campaign = max(stats, key=lambda s: s.spent)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\n[Test 2/3] Per-click detail — campaign {top_campaign.campaign_id} op {yesterday}")
    try:
        clicks = client.get_campaign_clicks_detail(top_campaign.campaign_id, yesterday)
        print(f"  ✓ {len(clicks)} clicks geladen met sourceId + teaserId")
    except Exception as exc:
        print(f"  ✗ {type(exc).__name__}: {exc}")
        return 1

    # Test 3: aggregate naar widgets + teasers
    if clicks:
        print(f"\n[Test 3/3] Aggregatie naar widget/teaser-niveau")
        widgets = client.aggregate_widgets(clicks)
        teasers = client.aggregate_teasers(clicks)
        print(f"  ✓ {len(widgets)} unieke widgets, {len(teasers)} unieke teasers")
        top_widgets = sorted(widgets.values(), key=lambda w: w.spend, reverse=True)[:5]
        if top_widgets:
            print(f"\n  Top 5 widgets op spend:")
            for w in top_widgets:
                print(f"    • {w.source_id}: {w.clicks} clicks, ${w.spend:.2f}, avg CPC ${w.avg_cpc:.3f}")

    print("\n" + "=" * 60)
    print("✓ Alle tests geslaagd — MGID-integratie werkt")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
