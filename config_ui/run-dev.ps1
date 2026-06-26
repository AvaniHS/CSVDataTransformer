# Config UI — Run scripts (Windows)

param(
    [ValidateSet("backend", "frontend", "all")]
    [string]$Target = "all"
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($Target -eq "backend" -or $Target -eq "all") {
    Write-Host "Starting backend on http://localhost:8002 ..."
    Start-Process -NoNewWindow py -ArgumentList "-3.12", "-m", "uvicorn", "config_ui.backend.app:app", "--host", "0.0.0.0", "--port", "8002", "--reload"
}

if ($Target -eq "frontend" -or $Target -eq "all") {
    Set-Location "$Root\config_ui\frontend"
    Write-Host "Starting frontend on http://localhost:5173 ..."
    npm run dev
}
