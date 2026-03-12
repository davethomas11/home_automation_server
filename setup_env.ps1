<#
.SYNOPSIS
    Bootstrap the development environment.
    Run this once after installing Python 3.11.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "Environment Setup" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

# 1. Locate Python 3.11 via pyenv-win first, then fallback to PATH
$PythonExe = $null

$PyenvRoot = Join-Path $env:USERPROFILE ".pyenv\pyenv-win"
if (Test-Path $PyenvRoot) {
    $versionsDir = Join-Path $PyenvRoot "versions"
    if (Test-Path $versionsDir) {
        $pyenvVersions = Get-ChildItem $versionsDir -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "^3\.11" } |
            Sort-Object Name -Descending
        foreach ($v in $pyenvVersions) {
            $candidate = Join-Path $v.FullName "python.exe"
            if (Test-Path $candidate) {
                $PythonExe = $candidate
                break
            }
        }
    }
}

if (-not $PythonExe) {
    $candidates = @(
        "python3.11",
        "python3",
        "python",
        "C:\Python311\python.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe")
    )
    foreach ($c in $candidates) {
        try {
            $ver = & $c --version 2>&1
            if ($ver -match "3\.11") {
                $PythonExe = $c
                break
            }
        } catch {
            # not found, continue
        }
    }
}

if (-not $PythonExe) {
    Write-Host ""
    Write-Host "ERROR: Python 3.11 not found." -ForegroundColor Red
    Write-Host "  Install it from https://www.python.org/downloads/ or via:" -ForegroundColor Yellow
    Write-Host "    pyenv install 3.11.7" -ForegroundColor Yellow
    Write-Host "  Then re-run this script." -ForegroundColor Yellow
    exit 1
}

$pyVer = & $PythonExe --version 2>&1
Write-Host ""
Write-Host "Using Python: $pyVer" -ForegroundColor Green
Write-Host "  Path: $PythonExe" -ForegroundColor DarkGray

# 2. Create virtual environment
$VenvPath = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host ""
    Write-Host "Creating virtual environment at .venv ..." -ForegroundColor Cyan
    & $PythonExe -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "Virtual environment already exists - skipping creation." -ForegroundColor Yellow
}

# 3. Install dependencies
$PythonVenv = Join-Path $VenvPath "Scripts\python.exe"

Write-Host ""
Write-Host "Upgrading pip, setuptools and wheel ..." -ForegroundColor Cyan
& $PythonVenv -m pip install --upgrade pip setuptools wheel --quiet

Write-Host "Installing project dependencies ..." -ForegroundColor Cyan
& $PythonVenv -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip install failed." -ForegroundColor Red
    exit 1
}

# 4. Ensure data directory exists
$DataDir = Join-Path $ProjectRoot "data"
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

# 5. Run Alembic migrations
Write-Host ""
Write-Host "Running database migrations ..." -ForegroundColor Cyan
& $PythonVenv -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Alembic migration failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the server:" -ForegroundColor Cyan
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host "  uvicorn home_automation_server.main:app --reload"
Write-Host ""
Write-Host "Then open:" -ForegroundColor Cyan
Write-Host "  http://127.0.0.1:8000       -> Dashboard UI"
Write-Host "  http://127.0.0.1:8000/docs  -> Swagger API docs"
Write-Host ""


