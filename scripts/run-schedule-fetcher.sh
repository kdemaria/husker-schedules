#!/bin/bash
# Cron entry point for the schedule fetcher.
# Activates the virtualenv, runs the fetcher, and captures output into a
# size-bounded cron log. The cron job should call this script directly with
# NO output redirection -- this wrapper manages its own logging.
set -u

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit 1

LOG="$PROJECT_DIR/logs/cron.log"
mkdir -p "$PROJECT_DIR/logs"

# Rotate the cron log before we start appending, so it stays bounded.
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 1000000 ]; then
    mv -f "$LOG" "$LOG.1"
fi
exec >> "$LOG" 2>&1

echo "=== run started $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
source "$PROJECT_DIR/venv/bin/activate" || exit 1
python3 "$PROJECT_DIR/scripts/schedule_fetcher.py"
RC=$?
echo "=== run finished rc=$RC $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
exit $RC
