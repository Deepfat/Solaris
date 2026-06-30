# ================================
# create_SolarisScheduler.ps1 v4
# Creates 3 scheduled tasks:
#   - Solar1Min   (every minute)
#   - Solar15Min  (every 15 minutes)
#   - SolarDaily  (once per day at 23:57)
# ================================

Write-Host "Installing Solaris scheduled tasks..." -ForegroundColor Cyan

# --- CONFIGURE YOUR PATHS HERE ---
$projectRoot = "C:\Projects\Solaris"
$python = "$projectRoot\venv\Scripts\python.exe"
$scheduler = "$projectRoot\solaris_logger\scheduler.py"
# ---------------------------------

# Validate paths
if (-Not (Test-Path $python)) {
    Write-Host "ERROR: Python not found at $python" -ForegroundColor Red
    exit 1
}

if (-Not (Test-Path $scheduler)) {
    Write-Host "ERROR: scheduler.py not found at $scheduler" -ForegroundColor Red
    exit 1
}

# --- CREATE TASKS ---

# 1-MIN SUMMARY
schtasks /Create /TN "Solar1Min" `
    /TR "`"$python`" -m solaris_logger.scheduler --mode 1min" `
    /SC MINUTE /MO 1 /F `
    /RL LIMITED `
    /RU SYSTEM

# 15-MIN SUMMARY
schtasks /Create /TN "Solar15Min" `
    /TR "`"$python`" -m solaris_logger.scheduler --mode 15min" `
    /SC MINUTE /MO 15 /F `
    /RL LIMITED `
    /RU SYSTEM

# DAILY SUMMARY (23:57)
schtasks /Create /TN "SolarDaily" `
    /TR "`"$python`" -m solaris_logger.scheduler --mode daily" `
    /SC DAILY /ST 23:57 /F `
    /RL LIMITED `
    /RU SYSTEM

Write-Host "Solaris scheduled tasks installed successfully." -ForegroundColor Green
Write-Host ""
Write-Host "To verify tasks:" -ForegroundColor Cyan
Write-Host "  schtasks /Query /TN Solar1Min"
Write-Host "  schtasks /Query /TN Solar15Min"
Write-Host "  schtasks /Query /TN SolarDaily"
