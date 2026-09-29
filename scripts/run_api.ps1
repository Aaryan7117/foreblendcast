# Start the ForeBlendCast API on all interfaces so a phone on the same Wi-Fi can reach it.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts/run_api.ps1 [-Port 8000]
param([int]$Port = 8000)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
& $py -m pip install -q -r api/requirements.txt
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object -ExpandProperty IPAddress
Write-Host ""
Write-Host "ForeBlendCast API starting on port $Port" -ForegroundColor Green
Write-Host "  Emulator  -> http://10.0.2.2:$Port"
foreach ($ip in $ips) { Write-Host "  Phone/LAN -> http://${ip}:$Port   (enter this in the app's Settings)" }
Write-Host "  Docs      -> http://localhost:$Port/docs"
Write-Host ""
& $py -m uvicorn api.main:app --host 0.0.0.0 --port $Port --reload
