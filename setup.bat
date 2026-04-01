@echo off
echo === TradeTracker Setup ===
echo.

REM Check for Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found. Install from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    exit /b 1
)

python --version

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate and install
echo Installing dependencies...
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

REM Generate API key
echo.
echo === Generated API Key ===
echo.
python -c "import config; key = config.generate_api_key(); print(f'  {key}'); print(); print(f'Save this! To start TradeTracker:'); print(); print(f'  venv\\Scripts\\activate'); print(f'  set TRADETRACKER_API_KEY={key}'); print(f'  python main.py'); print(); print(f'Then open: http://localhost:5050/?key={key}')"

echo.
echo === Setup Complete ===
pause
