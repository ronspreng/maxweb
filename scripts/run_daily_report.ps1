# PowerShell wrapper voor Windows Task Scheduler.
# Activeert venv, draait scripts/daily_report.py, logt naar logs/.
#
# Setup in Task Scheduler:
#   Program/script:   powershell.exe
#   Add arguments:    -ExecutionPolicy Bypass -File "C:\data\Claude\MaxWeb\scripts\run_daily_report.ps1"
#   Start in:         C:\data\Claude\MaxWeb
#
# Trigger: dagelijks om bv. 08:00.

$ErrorActionPreference = "Continue"
$projectRoot = "C:\data\Claude\MaxWeb"
Set-Location $projectRoot

# Activeer venv als die bestaat
if (Test-Path "$projectRoot\venv\Scripts\activate.ps1") {
    & "$projectRoot\venv\Scripts\activate.ps1"
}

# Run het rapport (default = last 1 day)
$logPath = "$projectRoot\logs\task_scheduler_$(Get-Date -Format 'yyyy-MM-dd').log"
"=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') Daily report start ===" | Out-File -Append -FilePath $logPath

try {
    python "$projectRoot\scripts\daily_report.py" --days 1 2>&1 | Out-File -Append -FilePath $logPath
    "=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') Daily report done ===" | Out-File -Append -FilePath $logPath
    exit 0
} catch {
    "FOUT: $_" | Out-File -Append -FilePath $logPath
    exit 1
}
