# MaxWeb Project Progress

## Sprint 1: Foundation (Week 1-2)

**Status:** Module 1 built, awaiting campaign start

### Definition of Done
- [x] Module 1 (Offer Intelligence) built and tested
- [x] Top-5 offers ranked via fit-score algorithm
- [ ] AM conversation completed (confirm offers, EPC's, caps)
- [ ] First campaign live on MGID ($200 test)
- [ ] ClickHub tracking active with sub-ID structure

### Build Tasks
- [x] CSV importer for MaxWeb offer data
- [x] Offer scoring algorithm (fit_score formula)
- [ ] SQLAlchemy models + migrations
- [x] CLI: `python -m src.module1_offers rank --budget 1500`
- [x] Pytest unit tests (edge cases)

### Campaign Tasks
- [ ] Pick offer from Module 1 top-3
- [ ] Write 1-2 headlines manually
- [ ] Create MGID account / campaign
- [ ] Setup ClickHub tracking with sub-IDs
- [ ] Deploy first ad ($200 budget)

### Notes
- Don't build other modules yet
- Focus on validated offer + working tracker
- Log all assumptions for post-mortem

---

## Sprint 2: Intelligence Layer (Week 3-4)

**Status:** Pending Sprint 1 completion

### Definition of Done
- [ ] Daily Mail scraper working, yields 50+ ads/week
- [ ] Pattern extraction (Claude API) generates report
- [ ] Second campaign live with Module 2 insights
- [ ] Competitive intel report in `/output/reports/`

### Build Tasks
- [ ] Playwright Daily Mail scraper
- [ ] Native ad extraction (Taboola/Outbrain detection)
- [ ] Deduplication logic
- [ ] Claude API pattern analyzer
- [ ] Database schema for native_ads table

### Campaign Tasks
- [ ] Analyze what's winning in market (Module 2)
- [ ] Generate 2nd set of headlines based on patterns
- [ ] Test against Module 1 campaign
- [ ] Track performance, adjust spend

---

## Sprint 3: Asset Creation (Week 5-6)

**Status:** Pending Sprint 2 completion

### Definition of Done
- [ ] Story advertorial template (Jinja2) working
- [ ] Generated pre-sell page deployed and live
- [ ] A/B test: generated page vs. direct link
- [ ] Compliance check (no hard claims, FTC disclaimer)

### Build Tasks
- [ ] Jinja2 template: story_advertorial.html.j2
- [ ] Generator that produces HTML from offer + angle
- [ ] Compliance checker (Claude API or heuristic)
- [ ] Deployment script (rsync to VPS)

### Campaign Tasks
- [ ] Pick best angle from Module 2
- [ ] Generate pre-sell page
- [ ] Deploy to separate domain
- [ ] Setup A/B test (page vs. direct)
- [ ] Monitor conversion rate changes

---

## Sprint 4: Feedback Loop (Week 7-8)

**Status:** Pending Sprint 3 completion

### Definition of Done
- [ ] ClickHub data import working
- [ ] Weekly analysis report auto-generated
- [ ] Scale/kill decisions made from Module 5
- [ ] ROI tracking live

### Build Tasks
- [ ] ClickHub API/CSV reader
- [ ] Data import pipeline (clean + normalize)
- [ ] Weekly analyzer (Claude API)
- [ ] Report generator (Markdown)

### Campaign Tasks
- [ ] Collect 2-4 weeks of data
- [ ] Review Module 5 recommendations
- [ ] Scale top 20% performers
- [ ] Kill bottom 20% (ROI < -50%)
- [ ] Rotate new creatives in

---

## Sprint 5+: Scale or Pivot (Week 9-12)

**Status:** Pending Sprint 4 completion

### Decision Point

- **Working (ROI > 0%):** Add Module 3 (creative gen), launch 2nd network (RevContent), test 2nd offer
- **Stalled (no winners after 5+ tests):** Post-mortem, pivot, or stop

---

## Open Questions

- [ ] ClickHub API spec? (Public API or CSV-only?)
- [ ] MaxWeb offer caps and refund rates for top-3?
- [ ] VPS provider preference? (Hetzner, Contabo, AWS?)
- [ ] Domain rotation strategy? (Separate domain per network or per offer?)
- [ ] Tax structure at scale? (ZZP, corporation, etc.)

---

## Key Metrics to Track

- **Spend:** Total ad spend YTD
- **Clicks:** Total tracked clicks
- **Conversions:** Total sales
- **Revenue:** Total commission earned
- **ROI:** (Revenue - Spend) / Spend * 100%
- **EPC:** Earnings per click (Revenue / Clicks)
- **CPC:** Cost per click (Spend / Clicks)
- **Breakeven CPC:** Cost at which ROI = 0%

---

*Last updated: 2026-05-08*
