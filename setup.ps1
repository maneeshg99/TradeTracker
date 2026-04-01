Write-Host "=== TradeTracker Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check for Python
$python = $null
foreach ($cmd in @("python", "python3")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 10) {
                $python = $cmd
                Write-Host "Using $ver"
                break
            }
        }
    } catch {}
}

if (-not $python) {
    Write-Host "ERROR: Python 3.10+ is required but not found." -ForegroundColor Red
    Write-Host "Install from https://www.python.org/downloads/"
    Write-Host "Make sure to check 'Add Python to PATH' during install."
    exit 1
}

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    & $python -m venv venv
}

# Activate
Write-Host "Installing dependencies..."
& .\venv\Scripts\Activate.ps1
pip install -q -r requirements.txt

# Generate API key
Write-Host ""
Write-Host "=== Generated API Key ===" -ForegroundColor Green
Write-Host ""
$key = & python -c "import config; print(config.generate_api_key())"
Write-Host "  $key" -ForegroundColor Yellow
Write-Host ""
Write-Host "Save this! To start TradeTracker:"
Write-Host ""
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  `$env:TRADETRACKER_API_KEY=`"$key`"" -ForegroundColor White
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
Write-Host "Then open: http://localhost:5050/?key=$key" -ForegroundColor Cyan
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
