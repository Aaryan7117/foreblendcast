# Run one forecast cycle with the frozen weights and publish it to the dashboard.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts/run_cycle.ps1 -Cycle 2022-06-14
#
# To run it every day at 06:30 (after the 00 UTC model runs have arrived), register it once:
#   $action  = New-ScheduledTaskAction -Execute "powershell.exe" `
#              -Argument "-ExecutionPolicy Bypass -File `"$PSScriptRoot\run_cycle.ps1`""
#   $trigger = New-ScheduledTaskTrigger -Daily -At 06:30
#   Register-ScheduledTask -TaskName "ForeBlendCast cycle" -Action $action -Trigger $trigger
#
# Without -Cycle the script uses today's date. The archive in data/raw ends in 2022, so a
# scheduled run only produces output once a live feed writes that day's files to data/raw.
param([string]$Cycle = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd"))
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
New-Item -ItemType Directory -Force logs | Out-Null
$log = "logs\cycle_$Cycle.log"
& $py -m experiments.cycle --cycle $Cycle 2> $log
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cycle $Cycle produced no forecast. See $log" -ForegroundColor Red
    exit $LASTEXITCODE
}
robocopy results frontend\public\data /MIR /NFL /NDL /NJH /NJS | Out-Null
Write-Host "Cycle $Cycle published to results/ and frontend/public/data" -ForegroundColor Green
