# MaxWeb Affiliate Decision Support System

**Owner:** Ron  
**Doel:** Claude Code-systeem dat 80% van het zware denkwerk voor MaxWeb affiliate campagnes overneemt (5-10u/week operatie)  
**Markt:** US native ads (MGID, RevContent, Taboola) → pre-sell pages → MaxWeb VSL  
**Stack:** Python 3.11+ + Claude API + SQLite (lokaal, geen n8n)

---

## Code Standards

- **Python 3.11+**, strikt type hints overal (geen `Any`)
- **Pydantic** models voor alle data structuren
- **SQLAlchemy ORM** + Alembic migrations (geen raw SQL)
- **Click** of **Typer** voor CLI commando's
- **Pytest** voor tests (minstens happy path per module)
- **Black** + **Ruff** voor formatting

---

## Architecture Principles

1. **Modules zijn independent** — elk kan standalone draaien. Geen cross-module hardcoding.
2. **Geen secrets in code** — alles via `.env` (via `python-dotenv`)
3. **IO structuur strak:**
   - `/data/` — lokale SQLite DB + imports
   - `/output/` — generated pages, reports, creatives
   - `/logs/` — date-stamped per sessie
4. **Wat getest wordt**, draait ook geïsoleerd met test fixtures
5. **Logging in elke module** (`logging` stdlib, niet print)

---

## Project Structure (per plan sectie 3)

```
maxweb-system/
├── plan.md                    # Master spec (lees dit eerst!)
├── progress.md                # Sprint logs
├── SCRATCHPAD.md             # Sessie notes
├── CLAUDE.md                 # Dit bestand
├── .env.example
├── pyproject.toml
├── README.md
├── src/
│   ├── module1_offers/        # Offer ranker
│   ├── module2_competitive/   # Native ad scrapers + patterns
│   ├── module3_creative/      # Headline + angle generator
│   ├── module4_presell/       # HTML page builder
│   └── module5_feedback/      # ClickHub analyzer
├── data/ (gitignored)
├── output/ (gitignored)
├── logs/ (gitignored)
└── tests/
```

---

## Build Order (reactief, niet proactief)

**Sprint 1:** Module 1 (Offer ranking) + handmatige $200 test  
**Sprint 2:** Module 2 (Competitive intel) + iteratie  
**Sprint 3:** Module 4 (Pre-sell pages) + A/B test  
**Sprint 4:** Module 5 (Feedback loop) + schaal/kill  
**Sprint 5+:** Module 3 (creative gen) optioneel + multi-offer

Bouw **niet alles vooraf**. Volg: "Build project infrastructure reactively through actual work."

---

## When in Doubt

1. **Business logic vragen** → Vraag aan Ron (AM details, offer strategies, budget allocatie)
2. **Simpel blijven** — geen premature abstraction, geen hypothetische future-proofing
3. **Testen per module** — `pytest src/module1_offers/` moet draaien zonder andere modules
4. **Logs + debugging** — bij errors: log context, stuur rapport naar Ron

---

## Key Files & Commands

```bash
# Setup
python -m venv venv
.\venv\Scripts\activate
pip install -e .

# Module 1 - Offer ranking
python -m src.module1_offers rank --budget 1500 --output report.md

# Module 2 - Competitive intel (per site)
python -m src.module2_competitive scrape-dailymail --output ads.json

# Module 4 - Page generator
python -m src.module4_presell generate --offer gluco-savior --angle doctor-reveals

# Module 5 - Weekly analysis
python -m src.module5_feedback analyze --since 7d --output report.md

# Tests
pytest tests/ -v
```

---

## Critical Success Factors

- **Module 1** moet bovenaan. Geen campagne zonder ranked offers.
- **Sub-ID structuur in ClickHub** is **essentieel** voor Module 5 analyse. Setup EERST.
  ```
  {network}_{geo}_{device}_{daypart}_{ad_id}_{landing_id}
  # Voorbeeld: mgid_US-TX_desktop_morning_h047_lp03
  ```
- **Compliance check** in Module 4 — geen hard medical claims, FTC disclaimer altijd.
- **Time discipline:** Max 50% tooling, 50% actual campaigns. Geen analysis paralysis.

---

## Decision Matrix (snelle keuzes)

| Vraag | Antwoord bron |
|---|---|
| Welke offer proberen? | Module 1 top-3 + AM advies |
| Welke creative angles? | Module 2 winning patterns |
| Welk netwerk starten? | MGID eerst, RevContent week 4-6 |
| Wanneer schalen? | Module 5: ROI > +20% met stat. significance |
| Wanneer killen? | Module 5: ROI < -50% na 200+ clicks |

---

## Compliance & Legal

- **Scraping:** Publieke sites (Daily Mail, etc.), low request rate, desktop user-agent, respect robots.txt
  - **Reddit:** Currently disabled (May 2026) — Reddit blocks all automated requests (API, RSS, browser automation). Use alternative sources for competitive intelligence.
- **Pre-sell pages:** Story format, geen "cures/reverses/guaranteed", FTC disclaimer
- **ClickHub tracking:** GDPR/CCPA check vooraf (US-only focus, maar best practice)

---

## Contact & Escalation

- **Business questions** (offer strategy, AM contacts, budget decisions) → Ron
- **Bugs/blockers in code** → Debug, log context, escalate met reproducer
- **Compliance concerns** → Flag immediately, don't deploy

---

## Last Updated

Plan v1.0 — ingesteld bij project init
