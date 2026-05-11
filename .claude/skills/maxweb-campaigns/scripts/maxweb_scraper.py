"""
MaxWeb Affiliate Backoffice scraper — Campaigns
================================================

Roept de interne API van https://affiliates-backoffice.maxweb.com aan
en schrijft de Campaigns-tabel weg als CSV en JSON.

Authenticatie: vereist de `sessid3`-cookie van een ingelogde browsersessie.
              Login en 2FA voer je 1x handmatig uit in Chrome.

Gebruik:
    1) Login in https://affiliates-backoffice.maxweb.com (incl. 2FA)
    2) Kopieer de waarde van de cookie `sessid3`:
         DevTools (F12) -> Application -> Cookies -> sessid3 -> Value
    3) Zet hem in een .env naast dit script:
         MAXWEB_SESSID3=...plak.hier...
       OF geef hem mee als argument: python maxweb_scraper.py --sessid3 <waarde>
    4) python maxweb_scraper.py
       Output: campaigns.csv, campaigns.json (in dezelfde map als het script)

Vereist:
    pip install requests python-dotenv

Geen offici__le, gedocumenteerde API: endpoints kunnen zonder waarschuwing
wijzigen. Bij fouten: opnieuw afleiden via DevTools -> Network.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

API_BASE = "https://affiliates-backoffice-api.maxweb.com"
ORIGIN = "https://affiliates-backoffice.maxweb.com"

# Velden die we naar CSV exporteren (volgorde = kolomvolgorde)
CSV_FIELDS = [
    "account_id",
    "name",
    "category",
    "category_id_maxweb",
    "commissionplanname",
    "commissionplantype",
    "avg_ltv",            # product price
    "avg_payout",
    "epc_alltime",
    "conversion_rate_alltime",
    "refundrate_alltime",
    "visitors_alltime",
    "trending",
    "negative_score",
    "positive_score",
    "flag_approved",
    "auto_approve",
    "company_website",
    "product_image",
    "codename",
    "rr_record_id",
    "cartproductname",
    "resources_link",
    "restrictions_link",
    "manage_link",
]

# Velden die als float gecast moeten worden voor numeriek gebruik
NUMERIC_FIELDS = {
    "avg_ltv",
    "avg_payout",
    "epc_alltime",
    "conversion_rate_alltime",
    "refundrate_alltime",
    "visitors_alltime",
    "trending",
    "negative_score",
    "positive_score",
}


def build_session(sessid3: str, trust2fa: str | None = None) -> requests.Session:
    """Bouw een requests.Session met de juiste cookies + headers."""
    s = requests.Session()
    s.cookies.set("sessid3", sessid3, domain=".maxweb.com")
    if trust2fa:
        s.cookies.set("trust2fa", trust2fa, domain=".maxweb.com")
    s.headers.update(
        {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": ORIGIN,
            "Referer": f"{ORIGIN}/app",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
    )
    return s


def fetch(session: requests.Session, endpoint: str, params: dict | None = None) -> Any:
    """GET op API_BASE/endpoint en verwacht JSON met {result, data}."""
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    r = session.get(url, params=params, timeout=30, allow_redirects=False)
    if r.status_code in (301, 302, 303, 307, 308):
        raise RuntimeError(
            f"Redirect ontvangen ({r.status_code} -> {r.headers.get('Location')}). "
            "Sessie waarschijnlijk verlopen — log opnieuw in en update sessid3."
        )
    if r.status_code == 401:
        print(f"\nDEBUG 401: Cookies in request:", r.request.headers.get("Cookie", "EMPTY"))
        print(f"Response body: {r.text[:500]}")
        raise RuntimeError(f"401 Unauthorized. Check cookies. Response: {r.text[:200]}")
    r.raise_for_status()
    payload = r.json()
    if not isinstance(payload, dict) or payload.get("result") != 1:
        raise RuntimeError(f"API gaf geen success-response voor {endpoint}: {payload}")
    return payload.get("data", [])


def normalize_record(rec: dict) -> dict:
    """Maak alleen de kolommen uit CSV_FIELDS, cast numeric fields naar float."""
    out: dict[str, Any] = {}
    for k in CSV_FIELDS:
        v = rec.get(k, "")
        if k in NUMERIC_FIELDS and v not in (None, ""):
            try:
                out[k] = float(str(v).lstrip("0") or "0")
            except (TypeError, ValueError):
                out[k] = v
        else:
            out[k] = v
    return out


def save_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def save_json(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape MaxWeb Campaigns via interne API")
    parser.add_argument(
        "--sessid3",
        help="Waarde van de sessid3-cookie (anders gelezen uit env MAXWEB_SESSID3 of .env)",
    )
    parser.add_argument(
        "--trust2fa",
        dest="trust2fa",
        help="Waarde van de trust2fa-cookie (optioneel, anders gelezen uit env MAXWEB_TRUST2FA)",
    )
    parser.add_argument(
        "--out",
        default=str(Path(__file__).parent),
        help="Output-map (default: map van het script)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Schrijf ook campaigns_raw.json met alle ruwe velden van de API",
    )
    args = parser.parse_args()

    # Probeer .env te laden als die er is (optioneel)
    sessid3 = args.sessid3 or os.environ.get("MAXWEB_SESSID3")
    trust2fa = args.trust2fa or os.environ.get("MAXWEB_TRUST2FA")

    if not sessid3:
        try:
            from dotenv import load_dotenv  # type: ignore

            load_dotenv(Path(__file__).parent / ".env")
            sessid3 = os.environ.get("MAXWEB_SESSID3")
            trust2fa = os.environ.get("MAXWEB_TRUST2FA")
        except ImportError:
            pass

    if not sessid3:
        print(
            "ERROR: geen sessid3 gevonden. Gebruik --sessid3 <waarde> of zet "
            "MAXWEB_SESSID3 in je environment of .env.",
            file=sys.stderr,
        )
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = build_session(sessid3, trust2fa)

    print("Ophalen categories...")
    categories = fetch(session, "get-categories")
    cat_lookup = {str(c.get("id")): c.get("name") for c in categories}
    print(f"  {len(categories)} categorieen")

    print("Ophalen campaigns (get-popular-products)...")
    raw = fetch(session, "get-popular-products")
    print(f"  {len(raw)} campagnes")

    # Verrijk met categorienaam als die nog niet aanwezig is
    for rec in raw:
        if not rec.get("category"):
            rec["category"] = cat_lookup.get(str(rec.get("category_id_maxweb")), "")

    rows = [normalize_record(rec) for rec in raw]

    csv_path = out_dir / "campaigns.csv"
    json_path = out_dir / "campaigns.json"
    save_csv(rows, csv_path)
    save_json(rows, json_path)
    print(f"Geschreven: {csv_path}")
    print(f"Geschreven: {json_path}")

    if args.raw:
        raw_path = out_dir / "campaigns_raw.json"
        save_json(raw, raw_path)
        print(f"Geschreven: {raw_path}")

    # Korte sanity-check in stdout
    if rows:
        sample = rows[0]
        print(
            f"Voorbeeld: {sample['name']!r} — payout=${sample['avg_payout']} "
            f"epc=${sample['epc_alltime']} cr={sample['conversion_rate_alltime']}%"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
