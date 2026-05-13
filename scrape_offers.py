#!/usr/bin/env python
"""Quick CLI to scrape MaxWeb offers to data/campaigns.csv.

Wrapper rond de API-scraper in .claude/skills/maxweb-campaigns/scripts/.
Auth via de `MAXWEB_SESSID3` (en evt. `MAXWEB_TRUST2FA`) cookies in .env -
GEEN gebruikersnaam/wachtwoord nodig.

Hoe verkrijg ik de cookies?
  1) Login in https://affiliates-backoffice.maxweb.com (Chrome)
  2) F12 -> Application -> Cookies -> sessid3 (en trust2fa) -> Value
  3) Plak in .env als MAXWEB_SESSID3=... / MAXWEB_TRUST2FA=...

Gebruik:
    python scrape_offers.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
SCRAPER = (
    PROJECT_ROOT
    / ".claude"
    / "skills"
    / "maxweb-campaigns"
    / "scripts"
    / "maxweb_scraper.py"
)


def main() -> int:
    if not SCRAPER.exists():
        print(f"ERROR: scraper niet gevonden op {SCRAPER}", file=sys.stderr)
        return 1
    result = subprocess.run(
        [sys.executable, str(SCRAPER), "--out", "./data"],
        cwd=str(PROJECT_ROOT),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
