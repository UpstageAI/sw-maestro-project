# Backend (FastAPI + LangGraph) launcher
# Usage: from anywhere, .\scripts\run-backend.ps1
#
# LLM mode switch:
#   Default is mock (no external LLM call, template responses).
#   To call real Solar, set env vars BEFORE running:
#     $env:LLM_PROVIDER = 'upstage'
#     $env:UPSTAGE_API_KEY = 'up_xxx...'

# 1) Resolve project root from script location, so cwd doesn't matter.
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# 2) Python sanity check.
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-Host "[run-backend] ERROR: python not found in PATH" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}
Write-Host "[run-backend] python: $(python --version)" -ForegroundColor Cyan
Write-Host "[run-backend] project root: $projectRoot" -ForegroundColor Cyan

# 3) Install deps if missing.
$probe = python -c "import fastapi, uvicorn, langgraph" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[run-backend] dependencies missing - installing..." -ForegroundColor Yellow
    python -m pip install -r (Join-Path $projectRoot 'backend\requirements.txt')
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[run-backend] pip install failed" -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit $LASTEXITCODE
    }
}

# 4) Env vars. PYTHONPATH must be absolute so python can find the 'app' package.
$env:PYTHONPATH = Join-Path $projectRoot 'backend'

# Default to upstage so real LLM responses are used. Override by setting
# $env:LLM_PROVIDER = 'mock' before running for offline/fast testing.
if (-not $env:LLM_PROVIDER) { $env:LLM_PROVIDER = 'upstage' }
if (-not $env:UPSTAGE_BASE_URL) { $env:UPSTAGE_BASE_URL = 'https://api.upstage.ai/v1' }
if (-not $env:UPSTAGE_MODEL) { $env:UPSTAGE_MODEL = 'solar-pro3' }

# Default API key — keeps the script self-sufficient when run via .cmd.
# Override by setting $env:UPSTAGE_API_KEY in your shell before running.
if (-not $env:UPSTAGE_API_KEY) {
    $env:UPSTAGE_API_KEY = 'up_pkJiynm2nwFPvokEszjDvKbkHe10X'
}

if ($env:LLM_PROVIDER -eq 'upstage' -and -not $env:UPSTAGE_API_KEY) {
    Write-Host "[run-backend] ERROR: LLM_PROVIDER=upstage but UPSTAGE_API_KEY is empty" -ForegroundColor Red
    Write-Host "  Set it before running:  `$env:UPSTAGE_API_KEY = 'up_xxx...'"
    Read-Host "Press Enter to close"
    exit 1
}

# 5) Port 8000 check (offer kill if in use).
$busy = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($busy) {
    $existingPid = $busy.OwningProcess
    Write-Host "[run-backend] port 8000 occupied by PID $existingPid" -ForegroundColor Yellow
    $ans = Read-Host "  Kill existing process and continue? (y/N)"
    if ($ans -eq 'y' -or $ans -eq 'Y') {
        Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 800
        Write-Host "[run-backend] killed PID $existingPid" -ForegroundColor Cyan
    } else {
        Write-Host "[run-backend] aborted (port still in use)" -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
}

# 6) Launch.
Write-Host "[run-backend] PYTHONPATH = $env:PYTHONPATH" -ForegroundColor Cyan
Write-Host "[run-backend] LLM_PROVIDER = $env:LLM_PROVIDER" -ForegroundColor Cyan
if ($env:LLM_PROVIDER -eq 'upstage') {
    Write-Host "[run-backend] UPSTAGE_MODEL = $env:UPSTAGE_MODEL" -ForegroundColor Cyan
}
Write-Host "[run-backend] starting on http://localhost:8000" -ForegroundColor Green
Write-Host "  (Ctrl+C to stop)" -ForegroundColor DarkGray
Write-Host ""

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Write-Host ""
Read-Host "[run-backend] server stopped. Press Enter to close"
