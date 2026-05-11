# MaxWeb Affiliate Decision Support System

A Claude Code-powered system that automates 80% of the heavy thinking for MaxWeb affiliate campaigns, enabling solo operation with 5-10 hours/week.

## Quick Start

### 1. Setup

```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Unix

pip install -e ".[dev]"
```

### 2. Environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
copy .env.example .env
# Edit .env with:
# - ANTHROPIC_API_KEY (from Anthropic dashboard)
# - CLICKHUB_API_KEY (from your ClickHub tracker)
```

### 3. Read the Plan

Start with **`plan.md`** for full context on:
- Business model (native ads → pre-sell → MaxWeb VSL)
- 5 modules (offer intelligence, competitive intel, creative generation, pre-sell pages, feedback loop)
- Build roadmap (reactive, not proactive)
- Success metrics

### 4. Build Order

**Sprint 1:** Module 1 (Offer ranking) + handmatig $200 test  
**Sprint 2:** Module 2 (Competitive intelligence) + iteratie  
**Sprint 3:** Module 4 (Pre-sell page generator) + A/B test  
**Sprint 4:** Module 5 (ClickHub feedback loop) + schaal/kill  
**Sprint 5+:** Module 3 (creative generation) optioneel

## Module Commands

```bash
# Module 1 - Rank offers by fit score
python -m src.module1_offers rank --budget 1500

# Module 2 - Scrape native ads from Daily Mail
python -m src.module2_competitive scrape-dailymail --output ads.json

# Module 4 - Generate pre-sell page
python -m src.module4_presell generate --offer gluco-savior --angle doctor-reveals

# Module 5 - Weekly ClickHub analysis
python -m src.module5_feedback analyze --since 7d --output report.md

# Run tests
pytest tests/ -v
```

## Project Files

- **`plan.md`** — Master specification (read this first!)
- **`CLAUDE.md`** — Code standards and architecture principles
- **`progress.md`** — Sprint logs and what's done/pending
- **`SCRATCHPAD.md`** — Session-specific notes
- **`data/`** — Local SQLite database and imports (gitignored)
- **`output/`** — Generated pages, creatives, reports (gitignored)
- **`logs/`** — Date-stamped log files (gitignored)

## Key Principles

1. **Modules are independent** — each can run standalone
2. **All secrets via `.env`** — never hardcoded
3. **Build reactively** — don't over-engineer upfront
4. **Test as you go** — each module has unit tests
5. **Time discipline** — 50% tooling, 50% actual campaigns

## Critical Setup

- **ClickHub sub-ID structure** (required for Module 5 analysis):
  ```
  {network}_{geo}_{device}_{daypart}_{ad_id}_{landing_id}
  # Example: mgid_US-TX_desktop_morning_h047_lp03
  ```
- **Compliance** — Story format, no hard medical claims, FTC disclaimer
- **Scraping** — Low request rates, desktop user-agent, respect robots.txt

## Contact

Questions? Ask Ron (business logic, strategy, AM contacts).

---

**Version:** 0.1.0  
**Last updated:** [DATE]
