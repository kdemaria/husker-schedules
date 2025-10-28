#!/bin/bash
# Wrapper script for running schedule_fetcher.py via cron
# This script activates the virtual environment and runs the fetcher

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Activate virtual environment
source "$PROJECT_DIR/venv/bin/activate" || exit 1

# Run the schedule fetcher
python3 "$PROJECT_DIR/scripts/schedule_fetcher.py"

# Exit with the script's exit code
exit $?
