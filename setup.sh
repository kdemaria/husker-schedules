#!/bin/bash

# Nebraska Huskers Schedule Fetcher - Setup Script
# This script sets up the environment for the schedule fetcher

set -e

echo "========================================"
echo "Nebraska Huskers Schedule Fetcher Setup"
echo "========================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Get Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python version: $PYTHON_VERSION"
echo ""

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "ERROR: pip3 is not installed. Please install pip3."
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo ""

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo ""

# Create necessary directories
echo "Creating directory structure..."
mkdir -p config scripts tmp output logs
echo "Directories created."
echo ""

# Setup configuration files
if [ ! -f "config/.env" ]; then
    echo "Creating .env file from template..."
    cp config/.env.example config/.env
    echo "✓ config/.env created"
    echo ""
    echo "IMPORTANT: Please edit config/.env and add your Anthropic API key!"
    echo "  Get your API key from: https://console.anthropic.com/settings/keys"
    echo ""
else
    echo "config/.env already exists. Skipping."
    echo ""
fi

if [ ! -f "config/config.json" ]; then
    echo "Creating config.json from template..."
    cp config/config.json.example config/config.json
    echo "✓ config/config.json created"
    echo ""
else
    echo "config/config.json already exists. Skipping."
    echo ""
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x scripts/schedule_fetcher.py
chmod +x setup.sh
echo ""

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "Creating .gitignore..."
    cat > .gitignore << 'EOL'
# Environment and credentials
config/.env
*.env

# Python
venv/
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Logs
logs/*.log

# Temporary files
tmp/*
!tmp/.gitkeep

# Output files (optional - uncomment if you don't want to track output)
# output/*.csv
# output/*.html
# output/*.zip

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
EOL
    echo "✓ .gitignore created"
    echo ""
fi

# Create placeholder files to preserve empty directories in git
touch tmp/.gitkeep
touch logs/.gitkeep

echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Edit config/.env and add your ANTHROPIC_API_KEY"
echo "2. (Optional) Edit config/config.json to customize settings"
echo "3. Test the script: source venv/bin/activate && python3 scripts/schedule_fetcher.py"
echo "4. Set up cron job to run automatically (see README.md for instructions)"
echo "5. Configure web access to the output directory (see output/README.md)"
echo ""
echo "For more information, see README.md"
echo ""
