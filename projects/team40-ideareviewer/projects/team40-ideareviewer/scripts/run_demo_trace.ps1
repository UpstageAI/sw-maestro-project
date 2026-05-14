param(
    [switch]$Regen,
    [switch]$NoTrace,
    [switch]$SkipLangSmithCheck,
    [int]$LangSmithTimeoutMs = 5000,
    [string]$Prefix = "persona-reviewer-demo"
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

function Get-KeySource {
    param([string]$Name)

    $processValue = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($processValue)) {
        return "process env"
    }

    $envPath = Join-Path $root ".env"
    if (Test-Path $envPath) {
        $pattern = "^\s*$([regex]::Escape($Name))\s*="
        $match = Select-String -Path $envPath -Pattern $pattern -Quiet
        if ($match) {
            return ".env"
        }
    }

    return "missing"
}

if ($NoTrace) {
    $env:LANGSMITH_TRACING = "false"
    Remove-Item Env:\LANGSMITH_PROJECT -ErrorAction SilentlyContinue
    Remove-Item Env:\LANGCHAIN_TRACING_V2 -ErrorAction SilentlyContinue
} else {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $env:LANGSMITH_TRACING = "true"
    $env:LANGSMITH_PROJECT = "$Prefix-$timestamp"
    if ([string]::IsNullOrWhiteSpace($env:LANGSMITH_ENDPOINT)) {
        $env:LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"
    }
}

Write-Host "LangSmith tracing: $env:LANGSMITH_TRACING"
if ($NoTrace) {
    Write-Host "LangSmith project: disabled"
} else {
    Write-Host "LangSmith project: $env:LANGSMITH_PROJECT"
}
Write-Host "UPSTAGE_API_KEY: $(Get-KeySource 'UPSTAGE_API_KEY')"
Write-Host "LANGSMITH_API_KEY: $(Get-KeySource 'LANGSMITH_API_KEY')"

if ((Get-KeySource "UPSTAGE_API_KEY") -eq "missing") {
    Write-Warning "UPSTAGE_API_KEY is missing. The pipeline will fail before the first LLM call completes."
}

if (-not $NoTrace -and (Get-KeySource "LANGSMITH_API_KEY") -eq "missing") {
    Write-Warning "LANGSMITH_API_KEY is missing while tracing is enabled. LangSmith trace upload may fail."
}

$argsList = @("scripts\test_pipeline.py")
if ($Regen) {
    $argsList += "--regen"
}

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python executable not found: $python"
}

Write-Host "Command: $python $($argsList -join ' ')"
Write-Host "If output stops at STEP 2 before the first check mark, the first LLM node is still running."
Write-Host ""

if (-not $NoTrace -and -not $SkipLangSmithCheck) {
    Write-Host "Checking LangSmith API connectivity..."
    $healthCheck = @"
import os
import sys

from dotenv import load_dotenv
from langsmith import Client

load_dotenv(".env")

api_key = os.getenv("LANGSMITH_API_KEY")
if not api_key:
    print("LANGSMITH_API_KEY is missing after loading .env.", file=sys.stderr)
    raise SystemExit(2)

client = Client(
    api_key=api_key,
    api_url=os.getenv("LANGSMITH_ENDPOINT"),
    timeout_ms=$LangSmithTimeoutMs,
)
next(client.list_projects(limit=1), None)
print("LangSmith API connectivity OK")
"@

    $healthCheck | & $python -
    if ($LASTEXITCODE -ne 0) {
        throw "LangSmith health check failed. Retry with -NoTrace to verify the pipeline without tracing, or fix LANGSMITH_API_KEY / network access."
    }
    Write-Host ""
}

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
& $python @argsList
$exitCode = $LASTEXITCODE
$stopwatch.Stop()

Write-Host ""
Write-Host "Pipeline exited with code: $exitCode"
Write-Host ("Elapsed: {0:n1}s" -f $stopwatch.Elapsed.TotalSeconds)
if (-not $NoTrace) {
    Write-Host "LangSmith project: $env:LANGSMITH_PROJECT"
}

exit $exitCode
