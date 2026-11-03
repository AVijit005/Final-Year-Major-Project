# AI-Based Anti-Spoofing Online Exam Proctoring System Launcher
# Developer: Avijit Pal (@AVijit005)

$Host.UI.RawUI.WindowTitle = "AI-Based Anti-Spoofing Online Exam Proctoring System"
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  🎓 AI-Based Anti-Spoofing Online Exam Proctoring System" -ForegroundColor Green
Write-Host "  Developer: Avijit Pal (@AVijit005)" -ForegroundColor Yellow
Write-Host "=====================================================================`n" -ForegroundColor Cyan

# Check for Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Detected: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.10 from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check/Create venv
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "[*] Step 1/3: Creating virtual environment 'venv'..." -ForegroundColor Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment!" -ForegroundColor Red
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
Write-Host "  Default Student: student@test.com  /  123456" -ForegroundColor White
Write-Host "  Default Admin:   admin@test.com    /  admin123" -ForegroundColor White
Write-Host "---------------------------------------------------------------------`n" -ForegroundColor Yellow

# Auto-open browser
Start-Process "http://localhost:5000"

# Start Flask
python app.py
