#!/usr/bin/env bash
set -e

echo "====================================================================="
echo "  🎓 AI-Based Anti-Spoofing Online Exam Proctoring System"
echo "  Developer: Avijit Pal (@AVijit005)"
echo "====================================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[*] Step 1/3: Creating virtual environment 'venv'..."
    python3 -m venv venv
    echo "[OK] Virtual environment created."
fi

source venv/bin/activate

if [ ! -f "venv/.installed" ]; then
    echo "[*] Step 2/3: Installing dependencies from requirements.txt..."
    pip install --upgrade pip > /dev/null 2>&1 || true
    pip install -r requirements.txt || true
    touch venv/.installed
    echo "[OK] Dependencies installed."
fi

echo ""
echo "[*] Step 3/3: Launching AI Proctoring Server..."
echo "---------------------------------------------------------------------"
echo "  Server running at: http://localhost:5000"
echo "  Default Student:   student@test.com  /  123456"
echo "  Default Admin:     admin@test.com    /  admin123"
echo "---------------------------------------------------------------------"
echo ""

# Auto-open browser
if which xdg-open > /dev/null; then
    (sleep 2 && xdg-open http://localhost:5000) &
elif which open > /dev/null; then
    (sleep 2 && open http://localhost:5000) &
fi

python3 app.py
