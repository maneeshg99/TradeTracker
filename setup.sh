#!/usr/bin/env bash
set -e

echo "=== TradeTracker Setup ==="
echo ""

# Check Python version
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$("$cmd" -c "import sys; print(sys.version_info.major)")
        minor=$("$cmd" -c "import sys; print(sys.version_info.minor)")
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.10+ is required but not found."
    echo "Install it from https://www.python.org/downloads/"
    exit 1
fi
echo "Using $PYTHON ($($PYTHON --version))"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv venv
fi

# Activate and install
echo "Installing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# Generate API key if not set
if [ -z "$TRADETRACKER_API_KEY" ]; then
    KEY=$(python -c "import config; print(config.generate_api_key())")
    echo ""
    echo "=== Generated API Key ==="
    echo ""
    echo "  $KEY"
    echo ""
    echo "Save this! You'll need it to access the web UI."
    echo ""
    echo "To start TradeTracker:"
    echo ""
    echo "  source venv/bin/activate"
    echo "  TRADETRACKER_API_KEY=$KEY python main.py"
    echo ""
    echo "Then open: http://localhost:5050/?key=$KEY"
else
    echo ""
    echo "TRADETRACKER_API_KEY is already set."
    echo ""
    echo "To start TradeTracker:"
    echo ""
    echo "  source venv/bin/activate"
    echo "  python main.py"
fi

echo ""
echo "=== Setup Complete ==="
