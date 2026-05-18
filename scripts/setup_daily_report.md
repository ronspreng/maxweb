# Daily Report — automatische dagelijkse uitvoering

`scripts/daily_report.py` analyseert al je ClickHub-campagnes en schrijft een
geaggregeerd kill/scale-rapport. Om dat dagelijks automatisch te draaien op
Windows: gebruik Task Scheduler.

## Eerste keer — handmatige run om te testen

```powershell
cd C:\data\Claude\MaxWeb
.\venv\Scripts\activate
python scripts\daily_report.py --days 1
```

Output landt in `data/daily_reports/YYYY-MM-DD.md`. Logs in `logs/daily_report_YYYY-MM-DD.log`.

## Task Scheduler opzetten (Windows 10/11)

1. **Open Task Scheduler** (`Win+R` → `taskschd.msc`)
2. **Action → Create Task** (niet "Create Basic Task" — die heeft minder opties)
3. **General tab**:
   - Name: `MaxWeb Daily Report`
   - Description: "Dagelijkse ClickHub-analyse + kill/scale flags"
   - Selecteer: *"Run whether user is logged on or not"*
   - ✓ *"Run with highest privileges"*
4. **Triggers tab → New**:
   - Begin the task: *On a schedule*
   - Daily, start: morgenochtend 08:00
   - Recur every: 1 day
   - ✓ Enabled
5. **Actions tab → New**:
   - Action: *Start a program*
   - Program/script: `powershell.exe`
   - Add arguments:
     ```
     -ExecutionPolicy Bypass -File "C:\data\Claude\MaxWeb\scripts\run_daily_report.ps1"
     ```
   - Start in: `C:\data\Claude\MaxWeb`
6. **Conditions tab**:
   - ✗ uncheck *"Start task only if computer is on AC power"* (anders skipt 'ie op laptop op accu)
   - ✓ *"Wake the computer to run this task"* (optioneel — laat hem op afgesloten Windows opstarten)
7. **Settings tab**:
   - ✓ *"Allow task to be run on demand"*
   - ✓ *"If the task fails, restart every: 10 minutes, attempt up to 3 times"*
   - If the running task does not end when requested, force it to stop: ✓
8. **OK** — Windows vraagt om je wachtwoord (voor "Run whether logged on or not")

## Testen of de scheduled task werkt

In Task Scheduler:
- Rechts-klik op de task → **Run** (forceert directe uitvoering)
- Check `logs/task_scheduler_YYYY-MM-DD.log` voor output
- Check `data/daily_reports/YYYY-MM-DD.md` voor rapport

## Optioneel: Discord notificaties

Voeg een Discord webhook toe in `.env`:
```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Bij elke run krijg je dan in je Discord-channel een korte samenvatting:
> **📊 Daily Campaign Report — 2026-05-15**
> • 5 active campaigns
> • 🚀 Scale: 2 · ❌ Kill: 1
> • Profit (24h): $87.30
> • Full report: `data/daily_reports/2026-05-15.md`

Webhook aanmaken: Discord server → Settings → Integrations → Webhooks → New Webhook.

## Geen Windows? Cron-equivalent (Mac/Linux)

```cron
# /etc/crontab — dagelijks om 08:00
0 8 * * * cd /path/to/MaxWeb && ./venv/bin/python scripts/daily_report.py --days 1
```
