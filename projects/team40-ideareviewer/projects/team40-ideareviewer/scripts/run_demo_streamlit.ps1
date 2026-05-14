param(
    [switch]$NoTrace,
    [string]$Prefix = "persona-reviewer-demo",
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Get-KeySource($Name) {
    if (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name, "Process"))) {
        return "process env"
    }
    if (Test-Path ".env") {
        $pattern = "^\s*$([regex]::Escape($Name))\s*="
        if (Select-String -Path ".env" -Pattern $pattern -Quiet) {
            return ".env"
        }
    }
    return "missing"
}

if ($NoTrace) {
    $env:LANGSMITH_TRACING = "false"
    Remove-Item Env:\LANGSMITH_PROJECT -ErrorAction SilentlyContinue
}
else {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $env:LANGSMITH_TRACING = "true"
    $env:LANGSMITH_PROJECT = "$Prefix-$timestamp"
    if ([string]::IsNullOrWhiteSpace($env:LANGSMITH_ENDPOINT)) {
        $env:LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"
    }
}

# Keep tracing configuration on the current LangSmith env surface.
Remove-Item Env:\LANGCHAIN_TRACING_V2 -ErrorAction SilentlyContinue

$streamlit = Join-Path $Root ".venv\Scripts\streamlit.exe"
if (-not (Test-Path $streamlit)) {
    throw "Streamlit executable not found: $streamlit"
}

Write-Host "LangSmith tracing: $env:LANGSMITH_TRACING"
if ($env:LANGSMITH_PROJECT) {
    Write-Host "LangSmith project: $env:LANGSMITH_PROJECT"
}
Write-Host "UPSTAGE_API_KEY: $(Get-KeySource 'UPSTAGE_API_KEY')"
Write-Host "LANGSMITH_API_KEY: $(Get-KeySource 'LANGSMITH_API_KEY')"
Write-Host "Streamlit URL: http://localhost:$Port"
Write-Host ""

& $streamlit run app.py --server.port $Port
exit $LASTEXITCODE
