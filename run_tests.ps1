param(
    [string]$Service = "all"
)

$ErrorActionPreference = "Continue"
$Results = @{}

$ROOT = (Get-Location).Path

$ENV = @(
    "-e", "NEO4J_URI=bolt://fake:7687",
    "-e", "NEO4J_USER=neo4j",
    "-e", "NEO4J_PASSWORD=test",
    "-e", "NEO4J_DATABASE=neo4j",
    "-e", "JWT_SECRET_KEY=test-secret-key",
    "-e", "JWT_ALGORITHM=HS256",
    "-e", "AMQP_URL=amqp://guest:guest@fake/",
    "-e", "CELERY_BROKER_URL=amqp://guest:guest@fake/",
    "-e", "CELERY_BACKEND_URL=redis://fake:6379/0",
    "-e", "OLLAMA_HOST=http://fake:11434",
    "-e", "OTEL_EXPORTER_OTLP_ENDPOINT=http://fake:4318/v1/traces"
)

$CMD = "pip install --quiet pytest pytest-asyncio httpx pytest-mock && pytest tests/ -v --tb=short"

function Run-Tests {
    param([string]$Name, [string]$Image, [string]$HostPath)

    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  RUNNING: $Name" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan

    $args = @("run", "--rm", "--pull", "never", "-v", "${HostPath}:/app", "-w", "/app") + $ENV + @($Image, "sh", "-c", $CMD)
    & docker @args
    $Results[$Name] = $LASTEXITCODE
}

switch ($Service) {
    "reader"  { Run-Tests "RecommendationsReader" "dyplom-recommendationsreader" "$ROOT\microservices\RecommendationsReader" }
    "server"  { Run-Tests "server"               "dyplom-fastapi-server"        "$ROOT\server" }
    "rawdata" { Run-Tests "RawDataCollector"      "dyplom-rawdatacollector"      "$ROOT\microservices\RawDataCollector" }
    "builder" { Run-Tests "RecommendationsBuilder" "dyplom-reco_base"             "$ROOT\microservices\RecommendationsBuilder" }
    "all" {
        Run-Tests "RecommendationsReader" "dyplom-recommendationsreader" "$ROOT\microservices\RecommendationsReader"
        Run-Tests "server"               "dyplom-fastapi-server"        "$ROOT\server"
        Run-Tests "RawDataCollector"     "dyplom-rawdatacollector"      "$ROOT\microservices\RawDataCollector"
        Run-Tests "RecommendationsBuilder" "dyplom-reco_base"            "$ROOT\microservices\RecommendationsBuilder"
    }
    default {
        Write-Host "Unknown service: $Service" -ForegroundColor Red
        Write-Host "Usage: .\run_tests.ps1 [-Service all|reader|server|rawdata|builder]"
        exit 1
    }
}

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor White
Write-Host "  SUMMARY" -ForegroundColor White
Write-Host ("=" * 60) -ForegroundColor White

$AllPassed = $true
foreach ($Svc in $Results.Keys) {
    if ($Results[$Svc] -eq 0) {
        Write-Host "  PASS  $Svc" -ForegroundColor Green
    } else {
        Write-Host "  FAIL  $Svc  (exit code: $($Results[$Svc]))" -ForegroundColor Red
        $AllPassed = $false
    }
}

Write-Host ""
if ($AllPassed) {
    Write-Host "All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some tests failed. Check output above." -ForegroundColor Red
    exit 1
}
