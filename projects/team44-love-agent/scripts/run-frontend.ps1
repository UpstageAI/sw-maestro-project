# Frontend (Next.js 15) dev server launcher
# Usage: from anywhere, .\scripts\run-frontend.ps1

# 1) Resolve project root from script location.
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# 2) Prepend portable Node to PATH if present (covers machines without system Node).
$portableNode = "$env:USERPROFILE\node-portable\node-v20.18.1-win-x64"
if (Test-Path $portableNode) {
    $env:PATH = "$portableNode;$env:PATH"
    Write-Host "[run-frontend] using portable Node at $portableNode" -ForegroundColor Cyan
}

# 3) Node sanity check.
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Host "[run-frontend] ERROR: node not found in PATH" -ForegroundColor Red
    Write-Host "  Install Node.js >= 18.18 (Next.js 15 requires it)."
    Write-Host "  Or place a portable Node at: $portableNode"
    Read-Host "Press Enter to close"
    exit 1
}
Write-Host "[run-frontend] node: $(node --version)" -ForegroundColor Cyan
Write-Host "[run-frontend] project root: $projectRoot" -ForegroundColor Cyan

# 4) Install deps if missing.
$nodeModules = Join-Path $projectRoot 'frontend\node_modules'
if (-not (Test-Path $nodeModules)) {
    Write-Host "[run-frontend] node_modules not found - installing..." -ForegroundColor Yellow
    npm --prefix (Join-Path $projectRoot 'frontend') ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[run-frontend] npm ci failed" -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit $LASTEXITCODE
    }
}

# 5) Port 3000 check.
$busy = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($busy) {
    $existingPid = $busy.OwningProcess
    Write-Host "[run-frontend] port 3000 occupied by PID $existingPid" -ForegroundColor Yellow
    $ans = Read-Host "  Kill existing process and continue? (y/N)"
    if ($ans -eq 'y' -or $ans -eq 'Y') {
        Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 800
        Write-Host "[run-frontend] killed PID $existingPid" -ForegroundColor Cyan
    } else {
        Write-Host "[run-frontend] aborted (port still in use - next would fall back to 3001)" -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
}

# 6) Launch.
Write-Host "[run-frontend] starting Next.js dev server on http://localhost:3000" -ForegroundColor Green
Write-Host "  (Ctrl+C to stop)" -ForegroundColor DarkGray
Write-Host ""

npm --prefix (Join-Path $projectRoot 'frontend') run dev

Write-Host ""
Read-Host "[run-frontend] server stopped. Press Enter to close"
