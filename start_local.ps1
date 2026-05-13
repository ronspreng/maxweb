# PowerShell script to start local testing

Write-Host "MaxWeb Local Testing Setup" -ForegroundColor Cyan
Write-Host ""

# Load environment variables from .env (if not already set)
Write-Host "[1] Loading environment variables..." -ForegroundColor Yellow
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$') {
            $name = $matches[1]
            $value = $matches[2].Trim('"').Trim("'")
            # ALTIJD overschrijven vanuit .env
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

# Defaults voor lokaal testen
if (-not $env:STREAMLIT_AUTH_ENABLED) { $env:STREAMLIT_AUTH_ENABLED = "true" }

if (-not $env:STREAMLIT_PASSWORD) {
    Write-Host "WARN: STREAMLIT_PASSWORD niet gezet" -ForegroundColor Red
    Write-Host "      Voeg toe aan .env: STREAMLIT_PASSWORD=<wachtwoord>" -ForegroundColor Red
} else {
    Write-Host "OK - STREAMLIT_PASSWORD geladen uit .env" -ForegroundColor Green
}
Write-Host "OK - STREAMLIT_AUTH_ENABLED = $($env:STREAMLIT_AUTH_ENABLED)" -ForegroundColor Green
Write-Host ""

# Check API Key
Write-Host "[2] Checking ANTHROPIC_API_KEY..." -ForegroundColor Yellow
if ($env:ANTHROPIC_API_KEY) {
    Write-Host "OK - API Key is set" -ForegroundColor Green
} else {
    Write-Host "Note: ANTHROPIC_API_KEY not in environment, checking .env..." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "WEBSITE (Port 8000)" -ForegroundColor Cyan
Write-Host "URL: http://localhost:8000" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "STREAMLIT APP (Port 8501)" -ForegroundColor Cyan
Write-Host "URL: http://localhost:8501" -ForegroundColor Green
Write-Host "Password: (zie .env STREAMLIT_PASSWORD)" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Starting servers..." -ForegroundColor Yellow
Write-Host ""

# Start website server in background
$websiteProcess = Start-Process python -ArgumentList "-m", "http.server", "8000" -WorkingDirectory "c:\data\Claude\MaxWeb\output\presell_site" -PassThru -WindowStyle Minimized
Write-Host "Website server started (PID: $($websiteProcess.Id))" -ForegroundColor Green

# Wait a moment
Start-Sleep -Seconds 2

# Start Streamlit in foreground
Set-Location "c:\data\Claude\MaxWeb"
Write-Host "Starting Streamlit app..." -ForegroundColor Green
Write-Host ""

streamlit run streamlit_app.py --server.port 8501 --server.address localhost

# Cleanup
Write-Host ""
Write-Host "Stopping website server..." -ForegroundColor Yellow
Stop-Process -Id $websiteProcess.Id -Force -ErrorAction SilentlyContinue
Write-Host "Done!" -ForegroundColor Green
