#
# ARCS One-Line Installer for Windows
# Usage: irm https://raw.githubusercontent.com/neooriginal/ARCS/main/install.ps1 | iex
#

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "    _    ____   ____ ____  " -ForegroundColor Cyan
Write-Host "   / \  |  _ \ / ___/ ___| " -ForegroundColor Cyan
Write-Host "  / _ \ | |_) | |   \___ \ " -ForegroundColor Cyan
Write-Host " / ___ \|  _ <| |___ ___) |" -ForegroundColor Cyan
Write-Host "/_/   \_\_| \_\____|____/ " -ForegroundColor Cyan
Write-Host ""
Write-Host "Autonomous Robot Control System - Installer" -ForegroundColor Green
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ $pythonVersion detected" -ForegroundColor Green
} catch {
    Write-Host "Error: Python 3 is required but not installed." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://python.org and try again."
    exit 1
}

# Check Git
try {
    $null = git --version
    Write-Host "✓ Git detected" -ForegroundColor Green
} catch {
    Write-Host "Error: Git is required but not installed." -ForegroundColor Red
    exit 1
}

# Install directory
$InstallDir = "$env:USERPROFILE\ARCS"

if (Test-Path $InstallDir) {
    Write-Host "Warning: $InstallDir already exists." -ForegroundColor Yellow
    $overwrite = Read-Host "Overwrite? (y/N)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "Installation cancelled."
        exit 0
    }
    Remove-Item -Recurse -Force $InstallDir
}

Write-Host ""
Write-Host "[1/5] Cloning ARCS repository..." -ForegroundColor Cyan
git clone --depth 1 https://github.com/neooriginal/ARCS.git $InstallDir
Set-Location $InstallDir

Write-Host "[2/5] Cloning hardware drivers..." -ForegroundColor Cyan
try {
    git clone --depth 1 -b custom https://github.com/neooriginal/RoboCrew.git robots/xlerobot 2>$null
} catch {
    # Ignore if already exists or fails
}

Write-Host "[3/5] Creating virtual environment..." -ForegroundColor Cyan
python -m venv venv
& .\venv\Scripts\Activate.ps1

Write-Host "[4/5] Installing Python dependencies..." -ForegroundColor Cyan
pip install --upgrade pip -q
pip install -r requirements.txt -q

Write-Host "[5/5] Setting up environment..." -ForegroundColor Cyan
Copy-Item .env.example .env

# Prompt for API key (Moved to Settings UI)
Write-Host ""
Write-Host "Note: Configure your OpenAI API Key in the Web UI Settings after installation." -ForegroundColor Yellow

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║       Installation Complete! 🎉            ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Directory: $InstallDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. cd $InstallDir"
Write-Host "  2. .\venv\Scripts\Activate.ps1"
Write-Host "  3. python main.py"
Write-Host ""
Write-Host "Open http://localhost:5000/settings to configure hardware." -ForegroundColor Cyan
Write-Host ""
