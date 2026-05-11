# MaxWeb Affiliate Decision Support System — Plan

> **Owner:** Ron
> **Doel:** Een Claude Code-gebouwd systeem dat 80% van het zware denkwerk voor MaxWeb affiliate campagnes overneemt, zodat solo operatie met 5-10u/week mogelijk wordt.
> **Markt:** US (geen EU compliance complicaties voor nutra/health)
> **Stack:** Pure Claude Code + Python + lokale SQLite + Claude API. **Geen n8n.**
> **Budget context:** $1.500-5.000 ad-spend over 2-3 maanden, parallel aan systeembouw.

---

## 1. Strategische Context (lees dit eerst)

### Het businessmodel

MaxWeb = CPA affiliate netwerk gespecialiseerd in nutra/health VSL offers met payouts $80-150 per sale. Het systeem moet helpen winstgevende campagnes op te zetten via **native ads** (MGID, RevContent, Taboola) richting **US 55-72 jarigen** op nieuwssites.

```
Native Ad ($0.20-0.80 CPC)
       ↓
Pre-sell Page (story-style advertorial)
       ↓
MaxWeb VSL (hun pagina, hun werk)
       ↓
Sale ($80-150 commissie)
```

### Core economics (waarom dit kan werken)
- Per 100 kliks: 0.5-2 sales = $40-300 omzet
- Break-even CPC: $0.40-1.60 (afhankelijk van offer + conversie)
- Win marge per campagne: 15-40% bij optimalisatie

### Waarom een systeem nodig is
- **Creative graveyard:** winnende ads leven 2-6 weken, dan herhalen
- **Solo affiliates concurreren tegen teams van 3-10 mensen** met $100K+/maand spend
- **5-10u/week is te weinig voor handmatig werk**, maar genoeg voor systeem-aangedreven werk
- **Edge zit in snelheid van iteratie**, niet in betere targeting (die hebben de groten al)

### Wat dit systeem NIET is
- ❌ Geen full automation pipeline (mensenkeuze blijft kritiek)
- ❌ Geen direct ad-deployment naar MGID/RevContent (geen API voor solo affiliates)
- ❌ Geen vervanging voor markt-intuïtie en creative judgment
- ❌ Geen wondermiddel — het versnelt werk dat je toch al moet doen

---

## 2. System Architecture (5 modules)

```
┌─────────────────────────────────────────────────────────┐
│  MODULE 1: OFFER INTELLIGENCE                           │
│  Wat: Rankt MaxWeb offers op fit-score voor jouw setup  │
│  Input: MaxWeb dashboard data (handmatig CSV / scrape)  │
│  Output: Top-5 offers met motivatie                     │
│  Build effort: 4-6 uur                                  │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  MODULE 2: COMPETITIVE INTELLIGENCE                     │
│  Wat: Verzamelt winnende native ad creatives uit markt  │
│  Input: Niche keyword + geo (US)                        │
│  Output: 20-50 winning angles + creative patterns       │
│  Build effort: 8-12 uur                                 │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  MODULE 3: CREATIVE GENERATION                          │
│  Wat: Genereert ad headlines + hooks op basis van data  │
│  Input: Offer + winning patterns                        │
│  Output: 30-50 headlines, 10 pre-sell angles            │
│  Build effort: 3-5 uur                                  │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  MODULE 4: PRE-SELL PAGE GENERATOR                      │
│  Wat: Bouwt complete HTML pre-sell pages                │
│  Input: Gekozen angle + offer details                   │
│  Output: Deploy-ready HTML pages (story format)         │
│  Build effort: 6-10 uur                                 │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│  MODULE 5: PERFORMANCE FEEDBACK LOOP                    │
│  Wat: Leest ClickHub data, geeft optimalisatie-advies   │
│  Input: ClickHub export/API                             │
│  Output: Welke combinaties schalen, welke killen        │
│  Build effort: 4-8 uur                                  │
└─────────────────────────────────────────────────────────┘
```

> **IMPORTANT:** Bouw deze modules **niet allemaal vooraf**. Volg het bouwprincipe uit eerdere Claude Code workflow guides: *"Build project infrastructure reactively through actual work rather than proactively."* Volgorde: Module 1 → handmatige campagne → Module 2 → tweede campagne → Module 4 → schalen → Module 5. Module 3 is optioneel als losse module (vaak voldoende als one-shot Claude API call).

---

## 3. Technische Stack

### Core dependencies
```
Python 3.11+
├── claude-sdk (Anthropic API)         # Module 3, 4, 5
├── playwright                          # Module 2 (scraping)
├── beautifulsoup4 + lxml              # Module 2 (HTML parsing)
├── pandas                              # Data wrangling
├── sqlalchemy + sqlite3               # Lokale opslag
├── jinja2                              # Module 4 (page templating)
├── requests + httpx                    # API calls
├── python-dotenv                       # Secrets management
└── click of typer                      # CLI interface
```

### Project structuur
```
maxweb-system/
├── plan.md                             # Dit document
├── progress.md                         # Wat is gedaan, wat volgt
├── SCRATCHPAD.md                       # Sessie notes
├── CLAUDE.md                           # Project conventies voor Claude Code
├── .env.example                        # Template voor secrets
├── pyproject.toml                      # Dependencies
├── README.md                           # Quickstart
│
├── src/
│   ├── module1_offers/
│   │   ├── __init__.py
│   │   ├── ranker.py                  # Offer scoring logic
│   │   ├── importer.py                # CSV/scrape MaxWeb data
│   │   └── prompts.py                 # Claude prompts voor analyse
│   │
│   ├── module2_competitive/
│   │   ├── __init__.py
│   │   ├── scrapers/
│   │   │   ├── dailymail.py
│   │   │   ├── msn.py
│   │   │   └── yahoo.py
│   │   ├── extractor.py               # Pattern extraction via Claude
│   │   └── storage.py
│   │
│   ├── module3_creative/
│   │   ├── __init__.py
│   │   ├── headlines.py
│   │   └── prompts.py
│   │
│   ├── module4_presell/
│   │   ├── __init__.py
│   │   ├── generator.py
│   │   ├── templates/
│   │   │   ├── story_advertorial.html.j2
│   │   │   ├── doctor_reveals.html.j2
│   │   │   └── before_after.html.j2
│   │   └── compliance_check.py
│   │
│   └── module5_feedback/
│       ├── __init__.py
│       ├── clickhub_reader.py
│       └── analyzer.py
│
├── data/
│   ├── offers.db                       # SQLite, alle data lokaal
│   └── exports/
│
├── output/
│   ├── presell_pages/                  # Generated HTML
│   ├── creatives/                      # Headlines, hooks, etc
│   └── reports/                        # Analyse rapporten
│
└── tests/
    └── ...
```

### Secrets management
```bash
# .env (NEVER commit)
ANTHROPIC_API_KEY=sk-ant-...
CLICKHUB_API_KEY=...
CLICKHUB_BASE_URL=https://tracker.clickhub.co/api
MAXWEB_USERNAME=...                    # voor scraping (optioneel)
MAXWEB_PASSWORD=...
```

---

## 4. Module 1: Offer Intelligence

### Doel
Inputs: ruwe offer-data uit MaxWeb dashboard (handmatig CSV export of Playwright scrape).
Output: top-5 offers gerankt op "fit-score" voor solo native ads operator met $1.500-5.000 budget.

### Scoring algoritme
```python
fit_score = (
    payout_score * 0.25 +           # >$80 = 1.0, $50-80 = 0.5, <$50 = 0.0
    epc_score * 0.25 +              # >$1.50 EPC = 1.0
    refund_score * 0.20 +           # <15% = 1.0, 15-25% = 0.5, >25% = 0.0
    competition_score * 0.15 +      # nieuwe offers > vol gespende offers
    age_stability_score * 0.10 +    # 6-12mo bestaande offers = 1.0 (boring=winner)
    geo_match_score * 0.05          # US offers = 1.0 voor onze focus
)
```

### Implementatie stappen
1. **CSV importer** - parse MaxWeb dashboard export
2. **Playwright scraper** (optioneel) - login + dashboard scrape voor live data
3. **Database schema** - offers tabel met snapshots over tijd
4. **Claude analyzer** - voor elke top-5 offer: 1-paragraph "why this fits" via API
5. **CLI command** - `python -m src.module1_offers rank --budget 1500`

### AM-vragen die het systeem opslaat
Het systeem moet je herinneren aan deze vragen voor je AM (per offer die je overweegt):
- "Average refund rate last 90 days?"
- "Top converting native ad creatives I can model from?"
- "Can offer absorb $500-1.000/day spend without cap issues?"
- "Best converting US geo's for this offer?"
- "Average EPC on native traffic specifically?"

> **NOTE:** Module 1 vereist nog geen ad-spend. Bouw deze eerst, dan parallel handmatig je eerste campagne starten met de #1 ranked offer.

---

## 5. Module 2: Competitive Intelligence

### Doel
Identificeer welke native ad creatives nu winnen in US health/nutra niche, zodat je geen creatives bouwt die al gefaald zijn.

### Bronnen (geen paid spy tools nodig)
**Tier 1 (gratis, breed):**
- Daily Mail US health/lifestyle sectie (heeft veel native ads van Taboola/Outbrain)
- MSN.com lifestyle/health
- Yahoo News health
- Fox News health (specifiek voor older conservative US demographic)

**Tier 2 (gratis, gefocused):**
- AOL Lifestyle (oudere Amerikaanse doelgroep)
- People.com health sectie
- Healthline comments/related sectie

**Tier 3 (paid, optioneel later):**
- Anstrex ($60/mo) - dedicated native ad spy
- AdPlexity Native ($199/mo) - premium

### Scraper architectuur
```python
class NativeAdScraper(ABC):
    def fetch_page(self, url: str) -> str: ...
    def extract_native_ads(self, html: str) -> list[NativeAd]: ...
    def deduplicate(self, ads: list[NativeAd]) -> list[NativeAd]: ...

class NativeAd(BaseModel):
    headline: str
    image_url: str
    landing_url: str
    source_site: str
    captured_at: datetime
    appearance_count: int  # hoe vaak gezien = signaal voor "winnend"
```

### Pattern extraction (via Claude API)
Na scraping stuur je 50-100 ads naar Claude met deze prompt-structuur:

```
Analyze these native ads from US health/nutra niche.
Identify:
1. Top 5 recurring HOOK patterns (e.g. "doctor reveals", "this one weird trick")
2. Top 5 emotional triggers (fear, curiosity, social proof, urgency)
3. Top 5 image archetypes (before/after, doctor stock, food close-up)
4. Headline word frequencies (most-used power words)
5. Patterns that appear in MULTIPLE ads (likely winners)

Output as structured JSON.
```

### Implementatie stappen
1. Bouw scraper voor 1 site (Daily Mail) - werkt het, dan andere
2. Database `native_ads` tabel
3. Run scraper dagelijks via cron / GitHub Action
4. Pattern extractor draait wekelijks op verzamelde data
5. Output: `output/reports/competitive_intel_YYYY-MM-DD.md`

> **IMPORTANT - Compliance:** Scraping van publieke pagina's voor research is grijs gebied. Houd request rates laag (1 per 5-10 sec), respecteer robots.txt waar mogelijk, gebruik desktop user-agent. Geen DDoS-achtige patterns.

---

## 6. Module 3: Creative Generation

### Doel
Op basis van Module 2's pattern data + gekozen offer details: genereer 30-50 ad headlines en 10 pre-sell angles.

### Aanpak
**Niet** een complex systeem. Gewoon goed gestructureerde Claude API calls met rijke context:

```python
def generate_headlines(offer: Offer, patterns: CompetitiveIntel, count: int = 30) -> list[str]:
    prompt = f"""
You are an expert direct response copywriter for US nutra native ads.

OFFER:
- Product: {offer.name}
- Category: {offer.category}
- Main benefit: {offer.primary_benefit}
- Target audience: US 55-72yo, middle-America, health-concerned

WINNING PATTERNS in current market (from {patterns.sample_size} ads):
- Top hooks: {patterns.top_hooks}
- Top emotional triggers: {patterns.top_triggers}
- Most-used power words: {patterns.power_words}

CONSTRAINTS:
- Headlines max 60 characters (native ad spec)
- No medical claims that violate US FTC guidelines
- Story-style preferred over hard sell
- Curiosity-driven > benefit-driven for native ads

Generate {count} headlines, each in a different angle/style.
Output as JSON array.
"""
```

### Output format
```json
{
  "headlines": [
    {
      "text": "Iowa Doctor Reveals 60-Second Morning Trick",
      "angle": "doctor_reveals",
      "trigger": "curiosity + authority",
      "estimated_ctr_tier": "high"
    },
    ...
  ]
}
```

### Iteratie loop
- Run elke 1-2 weken
- Save in DB met "tested/untested" status
- Module 5 koppelt headlines aan performance data

> **NOTE:** Dit is de simpelste module. Mogelijk slechts 1 Python file van 100 regels. Sla over als losse module en doe via Claude Code chat als je weinig tijd hebt.

---

## 7. Module 4: Pre-sell Page Generator

### Doel
Een gekozen angle (uit Module 3) omzetten in een complete, deploy-ready HTML pre-sell page.

### Page structuur (story advertorial format)
```
┌─────────────────────────────────────────┐
│ HERO HEADLINE (max 80 chars)            │
│ Sub-headline (curiosity gap)            │
│ [Hero Image - story protagonist]        │
├─────────────────────────────────────────┤
│ STORY OPENING                           │
│ "John, 62, from Cleveland..."           │
│ - Pain point setup                      │
│ - Failed attempts                       │
├─────────────────────────────────────────┤
│ DISCOVERY MOMENT                        │
│ - "Then he discovered..."               │
│ - Bridge naar product zonder           │
│   directe verkoop                       │
├─────────────────────────────────────────┤
│ TRANSFORMATION                          │
│ - Resultaten (verifieerbaar)            │
│ - Social proof elementen                │
├─────────────────────────────────────────┤
│ CTA                                      │
│ "Read his full story →"                 │
│ → Redirect naar MaxWeb VSL              │
└─────────────────────────────────────────┘
```

### Templates (Jinja2)
3 starting templates, elk een bewezen format:
1. `story_advertorial.html.j2` - "John's journey" stijl
2. `doctor_reveals.html.j2` - autoriteits-gebaseerd
3. `discovery_news.html.j2` - "scientists found" nieuws-stijl

### Compliance checker
```python
def check_compliance(html: str) -> ComplianceReport:
    """
    Detects:
    - Hard medical claims ("cures", "reverses", "guaranteed")
    - FTC violation triggers
    - Missing disclaimers
    - Aggressive scarcity tactics
    Returns warnings, not blocks.
    """
```

### Hosting / deployment
- Generated pages saved to `output/presell_pages/{offer_slug}/{angle}/index.html`
- Deploy via simpele rsync naar je VPS
- **NOTE:** gebruik separate domeinen per native ad network (Domein A voor MGID, B voor RevContent) om bans te isoleren
- Cloudflare proxy standaard voor alle domeinen

### Implementatie stappen
1. Bouw 1 template eerst (story_advertorial)
2. Generator die offer + angle → HTML produceert
3. Compliance check (Claude API call)
4. CLI: `python -m src.module4_presell generate --offer gluco-savior --angle doctor-reveals`
5. Output ready voor manual review + deploy

---

## 8. Module 5: Performance Feedback Loop

### Doel
ClickHub data binnentrekken, koppelen aan creative/page combinaties, en optimalisatie-advies geven.

### Data flow
```
ClickHub (campagne data)
    ↓ daily export (API of CSV)
Local DB (campaigns + clicks + conversions)
    ↓ analyzer
Markdown report met aanbevelingen
```

### ClickHub integratie
```python
# Twee opties:
# A) ClickHub API (als beschikbaar - check docs)
# B) CSV export uit dashboard, manual import

class ClickHubReader:
    def fetch_campaigns(self, since: datetime) -> list[Campaign]: ...
    def fetch_clicks(self, campaign_id: str) -> list[Click]: ...
    def fetch_conversions(self, campaign_id: str) -> list[Conversion]: ...
```

### Sub-ID structuur (kritiek voor analyse)
Stel je tracker zo in dat elke klik gelogd wordt met:
```
{network}_{geo}_{device}_{daypart}_{ad_id}_{landing_id}
```
Bijvoorbeeld:
```
mgid_US-TX_desktop_morning_h047_lp03
```

Hierdoor kan Module 5 analyseren:
- Welke geo+device combinatie converteert best?
- Welk daypart is goud (US ET morning rush)?
- Welke ad → landing combinatie wint?
- Welke creatives zijn "burning out" (CTR daalt over tijd)?

### Analyzer output (wekelijks rapport)
```markdown
# Weekly Campaign Analysis - Week 12

## Top Performers (scale these)
1. mgid_US-TX_desktop_morning_h047_lp03: ROI +47%, $312 profit
2. ...

## Burning Out (rotate creatives)
1. h023: CTR daalde van 0.8% naar 0.3% over 14 dagen

## Underperformers (kill or fix)
1. revcontent_US-CA_mobile_h055_lp01: -82% ROI, $-180

## New Hypotheses to Test
- Mobile + evening daypart underexploited (high CTR, low spend)
- Weather correlation: cold-front days = 23% higher conversions

## Action Items
- [ ] Scale h047 with 2x budget
- [ ] Generate 5 new headlines in h047 style
- [ ] Kill h055 series
```

### Claude API call voor weekly analysis
```python
def generate_weekly_report(week_data: WeekData) -> str:
    prompt = f"""
You are a senior native ad media buyer analyzing this week's data.

CAMPAIGNS (last 7 days):
{week_data.to_markdown()}

Identify:
1. Top 3 performers worth scaling (with specific scale-up advice)
2. Creatives that are burning out (CTR decline > 30%)
3. Hidden opportunities (high CTR but low spend)
4. Patterns across geo/device/daypart
5. Concrete action items for next week

Be direct and quantitative.
"""
```

> **IMPORTANT:** Module 5 heeft data nodig om waarde te leveren. **Bouw dit pas na 2-4 weken actieve campagnes.** Voor die tijd is het premature optimization.

---

## 9. Bouw Roadmap (parallel met campagnes)

### Sprint 1: Week 1-2 - Foundation
**Bouw:** Module 1 (Offer Intelligence)
**Campagne:** AM-gesprek + handmatige eerste $200 test op MGID
**Cashflow:** -$200

**Definition of done:**
- [ ] Module 1 ranked top-5 offers gegenereerd
- [ ] AM heeft top-3 offers en EPC's gedeeld
- [ ] Eerste handmatige campagne live op MGID
- [ ] ClickHub tracking actief met sub-ID structuur

### Sprint 2: Week 3-4 - Intelligence Layer
**Bouw:** Module 2 (Competitive Intel) - basis (Daily Mail scraper + extractor)
**Campagne:** Iteratie 1 op basis van eerste data + tweede creative test
**Cashflow:** -$300 tot -$500

**Definition of done:**
- [ ] Daily Mail scraper draait, levert 50+ unieke ads/week
- [ ] Eerste pattern extraction rapport gegenereerd
- [ ] Tweede campagne live met inzichten uit Module 2

### Sprint 3: Week 5-6 - Asset Creation
**Bouw:** Module 4 (Pre-sell Generator) - 1 template
**Campagne:** Test eigen pre-sell pages vs. direct linking
**Cashflow:** -$200 tot break-even

**Definition of done:**
- [ ] Story advertorial template werkend
- [ ] Eerste generated page live
- [ ] A/B test: gegenereerde page vs. baseline

### Sprint 4: Week 7-8 - Feedback Loop
**Bouw:** Module 5 (Performance Feedback) - basis
**Campagne:** Schaal winnende combinaties, kill verliezers
**Cashflow:** Break-even tot +$500 (mogelijk)

**Definition of done:**
- [ ] ClickHub data import werkend
- [ ] Eerste weekly report gegenereerd door Claude
- [ ] Beslissingen genomen op basis van Module 5 advies

### Sprint 5+: Week 9-12 - Schalen of pivoteren
**Beslismoment:** Werkt het systeem? ROI > 0%?
- **Ja:** Module 3 (creative gen) toevoegen, tweede netwerk (RevContent), tweede offer
- **Nee:** Post-mortem, één diepe iteratie, of beslissen te stoppen

---

## 10. Setup voor Claude Code

### CLAUDE.md (project conventies)
Maak een `CLAUDE.md` in project root met:
```markdown
# Project: MaxWeb Affiliate System

## Coding standards
- Python 3.11+, type hints overal
- Pydantic models voor data structuren
- SQLAlchemy ORM, geen raw SQL waar mogelijk
- Click of Typer voor CLI
- Pytest voor tests
- Black + ruff voor formatting

## Architecture principles
- Modules zijn independent (kunnen losstaand draaien)
- All API keys via .env, nooit hardcoded
- All output naar /output/, all data naar /data/
- Logs naar /logs/ met date-stamped files

## When in doubt
- Vraag aan mij voor business logic decisions
- Default naar simpel (geen over-engineering)
- Test elke module standalone voor integratie
```

### SCRATCHPAD.md
Sessie-specifieke notes. Hou bij:
- Welke offer ben ik nu aan het testen
- Welke hypotheses voor week X
- Open questions voor AM
- TODO items dat geen issue is

### progress.md
Wat is gebouwd, wat staat open. Update na elke sprint.

### Eerste Claude Code prompts om te starten

**Prompt 1 (project init):**
```
Lees plan.md. Initialize the project structure exactly as described
in section 3 ('Project structuur'). Setup pyproject.toml met de
dependencies in section 3 ('Core dependencies'). Setup .env.example,
.gitignore, README.md met quickstart. Maak een lege CLAUDE.md met
de inhoud uit section 10.

Build niets functioneel nog - alleen de structure.
```

**Prompt 2 (Module 1 build):**
```
Bouw Module 1 (Offer Intelligence) per sectie 4 in plan.md.

Fase 1: CSV importer
- Schema voor MaxWeb offer data (payout, EPC, refund_rate, age, geo's)
- CSV parser die deze velden mapt
- SQLAlchemy model + Alembic migration

Fase 2: Scoring algoritme
- Implementeer fit_score formule uit sectie 4
- Unit tests voor edge cases

Fase 3: CLI command
- `python -m src.module1_offers rank --budget 1500`
- Output: top 5 offers in tabular format + Markdown rapport

Vraag mij voor edge cases. Maak test data voor 10 fictieve offers.
```

**Prompt 3 (Module 2 - Daily Mail scraper):**
```
Bouw de Daily Mail scraper voor Module 2 per sectie 5 in plan.md.

Requirements:
- Playwright browser (headless)
- Random user agent rotation
- 5-10 sec delay tussen requests
- Detecteer Taboola/Outbrain native ad widgets
- Extract: headline, image_url, target_url, position
- Save to native_ads tabel met dedup logic

Test op 3 health-related Daily Mail artikelen. Toon mij 10 sample ads.
```

---

## 11. Risico's & Mitigaties

| Risico | Kans | Impact | Mitigatie |
|---|---|---|---|
| Account ban op MGID/RevContent | Medium | Hoog | Multiple domains, separate per network, Cloudflare proxy |
| MaxWeb offer paused mid-campaign | Medium | Medium | Vraag AM expliciet naar offer caps, hou backup offer klaar |
| Refund rate killt marges | Hoog | Hoog | Vraag refund data vóór start, kies offers <15% rate |
| 30-day hold cashflow probleem | Zeker | Medium | Plan vooraf, niet meer spend dan je 6-8 weken kunt missen |
| Concurrentie op winnende creatives | Hoog | Medium | Iteratie tempo, Module 3 voor nieuwe variants |
| Time sink: tooling > campagnes | Hoog | Hoog | Hard rule: max 50% tijd in tooling, 50% in campagnes |
| Compliance/legal issues | Laag (in US) | Hoog | Story format, geen hard claims, FTC disclaimer |

---

## 12. Definition of Success

**Niveau 1 (realistisch met 5-10u/week):**
- Maand 6: $500-1.500/maand consistent winst
- Systeem genereert zelfstandig wekelijkse aanbevelingen
- Eén stabiele winnende offer + 2-3 winning creatives in rotation

**Niveau 2 (vereist meer tijd of geluk):**
- Maand 12: $3.000-8.000/maand
- 2+ offers parallel, 2+ networks
- Module 5 stuurt 70% van beslissingen

**Faal-criteria (kill switch):**
- Maand 3: nog steeds geen winning campagne na 5+ tests
- Totaal verlies > $3.000
- Tijdsinvestering > 15u/week zonder winst zicht

> **Wanneer kill-switch raken: stop, doe post-mortem, beslis of je pivot doet of stopt.** Sunk cost is geen reden om door te gaan.

---

## 13. Referentie - Quick Decision Matrix

**Welke offer?** → Module 1 ranked top-3, kruisreferentie met AM advies
**Welke creative?** → Module 2 winnende patterns + Module 3 generatie
**Welk netwerk?** → Start MGID, voeg RevContent toe in week 4-6
**Welke geo?** → US-only, focus middle-America (TX, FL, OH, PA)
**Wanneer schalen?** → Module 5 zegt ROI > +20% met statistische significantie
**Wanneer killen?** → Module 5 zegt ROI < -50% na 200+ kliks

---

## 14. Open Vragen (update naarmate antwoorden komen)

- [ ] Heeft ClickHub een publieke API of alleen CSV export?
- [ ] Welke MaxWeb offers raadt AM aan voor native traffic specifiek?
- [ ] Is er een MaxWeb postback URL spec die ik moet implementeren?
- [ ] Welke VPS gebruiken voor pre-sell hosting? (Hetzner, Contabo, eigen homelab?)
- [ ] Tax setup: ZZP, eenmanszaak, of holdingstructuur bij doorbraak?

---

*Last updated: [DATE]*
*Version: 1.0*
