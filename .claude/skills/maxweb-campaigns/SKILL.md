---
name: maxweb-campaigns
description: Fetch, export, and analyze the user's MaxWeb affiliate campaigns (offers, payouts, EPC, conversion rates, traffic). Use this skill whenever the user mentions MaxWeb, affiliates-backoffice.maxweb.com, "campaigns", "offers", or asks anything about scraping, exporting, filtering, ranking, or comparing affiliate campaigns from MaxWeb — including questions like "top offers by EPC", "show me all Skin/Beauty campaigns above $50 payout", "give me a CSV of all my offers", or "refresh the campaigns data". Also trigger when the user wants to incorporate MaxWeb campaign data into a larger automation (price rules, ad-copy generation, dashboards, syncing to a sheet/database). The skill knows the internal API (no public API exists), how to authenticate via the sessid3 cookie, the field names and quirks (zero-padded numbers, etc.), and ships a Python scraper that writes campaigns.csv / campaigns.json.
---

# MaxWeb Campaigns

A skill for working with the user's MaxWeb affiliate-network campaign data. MaxWeb has no public API, so this skill uses a reverse-engineered internal endpoint that the backoffice SPA already calls. Authentication is purely via the user's session cookie — no API keys, no OAuth.

## When to use

- The user wants a fresh export of their campaigns (CSV, JSON, or in-memory dataframe).
- The user wants to filter, rank, or analyze their campaigns ("top 20 by EPC", "all Beauty offers with payout > $80", "campaigns where conversion rate dropped").
- The user is building automation that consumes MaxWeb data (sync to Sheets/DB, generate ad copy per top offer, price-rule engine, etc.).
- The user mentions issues with the existing scraper (auth errors, missing fields, schema changes).

## How it works at a glance

1. The user logs into `https://affiliates-backoffice.maxweb.com` in a browser (incl. 2FA — manual, one-time).
2. They copy the value of the `sessid3` cookie (DevTools → Application → Cookies).
3. The Python scraper (`scripts/maxweb_scraper.py`) calls the internal endpoint `https://affiliates-backoffice-api.maxweb.com/get-popular-products` with that cookie and writes `campaigns.csv` + `campaigns.json`.
4. From there you can load the CSV with pandas, query it, join it with other data, etc.

The endpoint returns ~500 records in a single GET — no pagination. Field details are in `references/data_dictionary.md`.

## Step-by-step usage

### 1. Make sure the scraper has fresh auth

Ask the user for a fresh `sessid3` value. Don't try to log in for them — credentials and 2FA codes are user-only territory.

If they already have a `.env` next to the script (`MAXWEB_SESSID3=...`), just use that. Otherwise prompt them to:

- Open `https://affiliates-backoffice.maxweb.com` in Chrome (logged in)
- F12 → Application → Cookies → `https://affiliates-backoffice.maxweb.com` → copy `sessid3` value
- Paste into `.env` or pass via `--sessid3` flag

If the scraper returns "Sessie waarschijnlijk verlopen", the cookie expired — ask for a new one.

### 2. Run the scraper

From the project root:

```bash
python .claude/skills/maxweb-campaigns/scripts/maxweb_scraper.py --out ./data
```

Outputs `data/campaigns.csv` and `data/campaigns.json`. Add `--raw` if you also want `campaigns_raw.json` with all unprocessed fields from the API.

The script depends only on `requests` (and optionally `python-dotenv`). Install with `pip install requests python-dotenv` if missing.

### 3. Use the data

For ad-hoc analysis, load the CSV with pandas:

```python
import pandas as pd
df = pd.read_csv("data/campaigns.csv")
top_epc = df.sort_values("epc_alltime", ascending=False).head(20)
```

For programmatic use inside a larger pipeline, you can also import the scraper as a library:

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(".claude/skills/maxweb-campaigns/scripts")))

from maxweb_scraper import build_session, fetch, normalize_record

session = build_session(os.environ["MAXWEB_SESSID3"])
raw = fetch(session, "get-popular-products")
records = [normalize_record(r) for r in raw]
```

The `normalize_record` function casts numeric fields (avg_payout, epc_alltime, etc.) from MaxWeb's zero-padded strings (`"000000000049.95"`) to proper floats and drops fields you don't typically need.

## Important quirks

**Zero-padded numerics.** Most numeric fields come back as strings like `"000000000049.95"`. The scraper handles this, but if you call the endpoint directly (e.g., from JavaScript or a different language), you'll need to strip leading zeros and parse to float yourself.

**Two account-id fields.** Each record has both `account_id` and `_account_id` — they're identical. The SPA used both for legacy reasons; the scraper exposes `account_id`.

**`category` may be empty.** Some records have only `category_id_maxweb` and not the resolved name. The scraper backfills from `/get-categories` (43 categories) — keep this join in mind if you bypass the scraper.

**`flag_approved` is a tri-state.** `0` = not approved for this affiliate, `1` = approved (rare), `2` = approved-and-active. Use `flag_approved >= 1` if you want everything you can promote.

**Cookie can expire mid-script.** A long-running pipeline should catch the redirect-on-auth-failure (script raises `RuntimeError` with "Sessie waarschijnlijk verlopen") and prompt for a refresh rather than crashing the whole batch.

**Endpoint is unofficial.** MaxWeb can change field names, drop the endpoint, or add CSRF protection at any time. If the script suddenly breaks: open DevTools → Network on the Campaigns page, look for the new XHR, and update `API_BASE` / endpoint name in the script. Reference the technique in `references/reverse_engineering.md`.

## Other endpoints (same pattern)

The MaxWeb SPA exposes more endpoints under the same `affiliates-backoffice-api.maxweb.com` host, all with the same cookie auth. They're not implemented in the scraper yet, but adding them is trivial — copy `fetch(session, "get-popular-products")` and swap the name. Useful ones:

- `get-categories` — already used internally, returns `[{id, name}, ...]`
- `get-promoted-offers` — only the offers this affiliate is actively promoting
- `get-pending-payments` / `get-completed-payments` — payout history
- `get-affiliate-links` — tracking URLs per offer
- `get-postback-pixels` / `get-external-pixels` — pixel configuration
- `promote-offer?offer_account_id=<id>` — request approval to promote a new offer (POST-style action)

See `references/api.md` for the full endpoint inventory observed in the SPA source.

## Common analysis patterns

When the user asks for analysis, refresh the data first (run the scraper) unless they explicitly say "use the existing CSV". Stale data is a frequent footgun for affiliate marketing where stats move daily.

Examples in `examples/`:
- `top_by_epc.py` — simplest case, pandas one-liner
- `analyze_campaigns.py` — categorical breakdown + filtering helpers, good template for new analyses

## Files in this skill

- `scripts/maxweb_scraper.py` — the scraper. Standalone runnable; also importable.
- `references/api.md` — endpoint inventory + auth notes.
- `references/data_dictionary.md` — every field returned by `get-popular-products`, with type and example.
- `references/reverse_engineering.md` — how the API was discovered, and how to repeat the process if MaxWeb breaks the contract.
- `examples/top_by_epc.py` — minimal analysis example.
- `examples/analyze_campaigns.py` — richer analysis template.
