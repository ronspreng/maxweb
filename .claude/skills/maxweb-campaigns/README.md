# maxweb-campaigns (Claude Code skill)

Drop this skill folder into any Claude Code project that needs to read MaxWeb affiliate campaign data.

## Install

Copy the entire `maxweb-campaigns/` folder into your project's `.claude/skills/` directory (create it if it doesn't exist):

```
your-project/
├── .claude/
│   └── skills/
│       └── maxweb-campaigns/   ← this folder
│           ├── SKILL.md
│           ├── scripts/
│           ├── references/
│           └── examples/
├── src/
└── ...
```

Claude Code auto-discovers skills under `.claude/skills/` at session start. No manual registration needed.

For a personal/cross-project skill, copy it to `~/.claude/skills/maxweb-campaigns/` instead.

## First-run setup

```bash
pip install requests python-dotenv
```

Then create a `.env` (anywhere your script can find it — root of project is fine) with your MaxWeb session cookie:

```
MAXWEB_SESSID3=<paste-from-DevTools>
```

How to get the cookie: log into `affiliates-backoffice.maxweb.com` in Chrome → F12 → Application → Cookies → copy `sessid3` value.

## Try it

In Claude Code, just ask:

- "Refresh my MaxWeb campaigns and show me top 10 by EPC"
- "Export all my campaigns to a CSV"
- "Which Beauty campaigns have payout above $50?"

Claude Code will pick up the skill, read SKILL.md, run the scraper, and answer.

## Manual run (without Claude)

```bash
python .claude/skills/maxweb-campaigns/scripts/maxweb_scraper.py --out ./data
```

Outputs `data/campaigns.csv` and `data/campaigns.json`.
