# AI-Based Anti-Spoofing Online Exam Proctoring System Launcher
# Developer: Avijit Pal (@AVijit005)

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
Set-Location -Path $PSScriptRoot

$Host.UI.RawUI.WindowTitle = "AI-Based Anti-Spoofing Online Exam Proctoring System"
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  [AI Proctoring] Online Exam Proctoring System" -ForegroundColor Green
Write-Host "  Developer: Avijit Pal (@AVijit005)" -ForegroundColor Yellow
Write-Host "=====================================================================`n" -ForegroundColor Cyan

# Check for Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Detected: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.10 from https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

# Check/Create venv
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "[*] Step 1/3: Creating virtual environment 'venv'..." -ForegroundColor Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment!" -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
} else {
    Write-Host "[OK] Existing virtual environment found." -ForegroundColor Green
}

# Activate
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
if (-not (Test-Path "venv\.installed")) {
    Write-Host "`n[*] Step 2/3: Installing required dependencies from requirements.txt..." -ForegroundColor Cyan
    python -m pip install --upgrade pip | Out-Null
    pip install -r requirements.txt
    Set-Content -Path "venv\.installed" -Value "1"
    Write-Host "[OK] Dependencies installed successfully." -ForegroundColor Green
} else {
    Write-Host "[OK] Dependencies already installed." -ForegroundColor Green
}

Write-Host "`n[*] Step 3/3: Launching AI Proctoring Server..." -ForegroundColor Cyan
Write-Host "---------------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "  Server URL:      http://localhost:5000" -ForegroundColor White
Write-Host "  Default Student: student@test.com   /  123456" -ForegroundColor White
Write-Host "  Demo Student 2:  student2@test.com  /  123456" -ForegroundColor White
Write-Host "  Default Admin:   admin@test.com     /  admin123" -ForegroundColor White
Write-Host "---------------------------------------------------------------------`n" -ForegroundColor Yellow

# Port 5000 check
$port5000 = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
if ($port5000) {
    Write-Host "[WARNING] Port 5000 is already in use! Close previous server instance if needed.`n" -ForegroundColor Yellow
}

# Auto-open browser after 2 seconds
Start-Job -ScriptBlock { Start-Sleep -Seconds 2; Start-Process "http://localhost:5000" } | Out-Null

# Start Flask
try {
    python app.py
} finally {
    Write-Host "`nServer terminated." -ForegroundColor Cyan
    Read-Host "Press Enter to exit..."
}
