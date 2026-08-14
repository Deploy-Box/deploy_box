<#
.SYNOPSIS
    Orchestrates the full Playwright E2E test run for Deploy Box.

.DESCRIPTION
    1. Starts the Docker Compose e2e stack (Postgres + Django)
    2. Waits for healthy containers
    3. Installs Playwright (if needed)
    4. Runs the Playwright tests
    5. Tears down the Docker stack

.EXAMPLE
    .\scripts\run-e2e.ps1                # Run all tests
    .\scripts\run-e2e.ps1 -SkipTeardown  # Leave containers running after tests
    .\scripts\run-e2e.ps1 -Headed        # Run tests in headed browser mode
#>

param(
    [switch]$SkipTeardown,
    [switch]$Headed,
    [switch]$UI
)

$ErrorActionPreference = "Stop"
$websiteDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
# If run from e2e/ directly, adjust
if ((Split-Path -Leaf $websiteDir) -eq "e2e") {
    $websiteDir = Split-Path -Parent $websiteDir
}
$e2eDir = Join-Path $websiteDir "e2e"
$composeFile = Join-Path $websiteDir "docker-compose.e2e.yml"

Write-Host "`n=== Deploy Box E2E Test Runner ===" -ForegroundColor Cyan

# ── 1. Start Docker stack ──────────────────────────────────────────────
Write-Host "`n[1/4] Starting Docker Compose stack..." -ForegroundColor Yellow
Push-Location $websiteDir
try {
    docker compose -f $composeFile up --build -d
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed to start" }
} finally {
    Pop-Location
}

# ── 2. Wait for Django to be healthy ───────────────────────────────────
Write-Host "`n[2/4] Waiting for Django to be healthy..." -ForegroundColor Yellow
$timeout = 120
$elapsed = 0
while ($elapsed -lt $timeout) {
    try {
        $status = docker inspect --format '{{.State.Health.Status}}' deploy-box-e2e-django 2>$null
        if ($status -eq "healthy") {
            Write-Host "  Django is healthy!" -ForegroundColor Green
            break
        }
    } catch {}
    Start-Sleep -Seconds 3
    $elapsed += 3
    Write-Host "  waiting... ($elapsed`s)" -ForegroundColor DarkGray
}
if ($elapsed -ge $timeout) {
    Write-Host "  Django did not become healthy within $timeout`s" -ForegroundColor Red
    Write-Host "  Container logs:" -ForegroundColor Red
    docker logs deploy-box-e2e-django --tail 50
    throw "Timeout waiting for Django"
}

# ── 3. Install Playwright deps if needed ───────────────────────────────
Write-Host "`n[3/4] Installing Playwright..." -ForegroundColor Yellow
Push-Location $e2eDir
try {
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    npx playwright install chromium --with-deps 2>$null
} finally {
    Pop-Location
}

# ── 4. Run tests ──────────────────────────────────────────────────────
Write-Host "`n[4/4] Running Playwright tests..." -ForegroundColor Yellow
Push-Location $e2eDir
$exitCode = 0
try {
    $args = @()
    if ($Headed) { $args += "--headed" }
    if ($UI) { $args += "--ui" }

    npx playwright test @args
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

# ── Teardown ──────────────────────────────────────────────────────────
if (-not $SkipTeardown) {
    Write-Host "`nTearing down Docker stack..." -ForegroundColor Yellow
    Push-Location $websiteDir
    docker compose -f $composeFile down -v
    Pop-Location
} else {
    Write-Host "`nSkipping teardown (-SkipTeardown). Clean up later with:" -ForegroundColor DarkYellow
    Write-Host "  docker compose -f docker-compose.e2e.yml down -v" -ForegroundColor DarkGray
}

# ── Summary ───────────────────────────────────────────────────────────
if ($exitCode -eq 0) {
    Write-Host "`n✅ All E2E tests passed!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Some E2E tests failed. Run 'npm run report' in e2e/ to see the HTML report." -ForegroundColor Red
}

exit $exitCode
