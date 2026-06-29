# ================================
# create_SolarisScheduler.ps1 v3
# Creates 3 scheduled tasks:
#   - Solar1Min   (every minute)
#   - Solar15Min  (every 15 minutes)
#   - SolarDaily  (once per day at 23:57)
# ================================

Write-Host "Installing Solaris scheduled tasks..." -ForegroundColor Cyan

# --- CONFIGURE YOUR PATHS HERE ---
$python = "C:\Python\python.exe"
$script = "C:\solaris\db_writer.py"
# ---------------------------------

# Validate paths
if (-Not (Test-Path $python)) {
    Write-Host "ERROR: Python not found at $python" -ForegroundColor Red
    exit 1
}

if (-Not (Test-Path $script)) {
    Write-Host "ERROR: db_writer.py not found at $script" -ForegroundColor Red
    exit 1
}

# --- CREATE TASKS ---

# 1-MIN SUMMARY
schtasks /Create /TN "Solar1Min" `
    /TR "`"$python`" `"$script`" --mode 1min" `
    /SC MINUTE /MO 1 /F `
    /RL LIMITED

# 15-MIN SUMMARY
schtasks /Create /TN "Solar15Min" `
    /TR "`"$python`" `"$script`" --mode 15min" `
    /SC MINUTE /MO 15 /F `
    /RL LIMITED

# DAILY SUMMARY (23:57)
schtasks /Create /TN "SolarDaily" `
    /TR "`"$python`" `"$script`" --mode daily" `
    /SC DAILY /ST 23:57 /F `
    /RL LIMITED

Write-Host "Solaris scheduled tasks installed successfully." -ForegroundColor Green
