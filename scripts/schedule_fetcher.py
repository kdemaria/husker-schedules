#!/usr/bin/env python3
"""Nebraska Huskers Schedule Fetcher.

For each sport, pulls the schedule from a prioritized list of sources
(huskers.com -> ESPN -> Claude API), validates the result, and writes a CSV.
If a sport cannot be produced by any source, the existing CSV is left in
place and an alert email is sent -- the run never fails silently.
"""
import csv
import datetime
import json
import logging
import os
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
LOG_DIR = BASE_DIR / "logs"
sys.path.insert(0, str(SCRIPTS_DIR))

from sources import espn, huskers, llm  # noqa: E402
from sources.common import CSV_COLUMNS  # noqa: E402
from html_generator import generate_schedule_html  # noqa: E402

logger = logging.getLogger("husker_schedules")

SOURCES = {"huskers": huskers, "espn": espn, "llm": llm}
DEFAULT_SOURCE_ORDER = ["huskers", "espn", "llm"]


def setup_logging():
    """Console + a bounded rolling log + a per-day log file."""
    LOG_DIR.mkdir(exist_ok=True)
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    rolling = RotatingFileHandler(
        LOG_DIR / "husker-schedules.log",
        maxBytes=1_000_000, backupCount=5)
    daily = logging.FileHandler(
        LOG_DIR / f"schedule_fetcher_{datetime.date.today():%Y%m%d}.log")
    console = logging.StreamHandler()
    for handler in (rolling, daily, console):
        handler.setFormatter(fmt)
        logger.addHandler(handler)


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("Config not found: %s (using defaults)", path)
        return default


def validate(games, sport_name):
    """Structural validation. Returns (ok, problems).

    Structural defects (missing date/opponent, unparseable date) are hard
    failures. A past game lacking a result is only a logged warning -- a
    just-finished game may not have a posted score yet.
    """
    if not games:
        return False, ["source returned no games"]

    today = datetime.date.today()
    problems = []
    past_without_result = 0
    for index, game in enumerate(games):
        if not game.get("opponent"):
            problems.append(f"row {index}: empty opponent")
        try:
            game_date = datetime.datetime.strptime(
                game.get("date", ""), "%m/%d/%Y").date()
        except ValueError:
            problems.append(f"row {index}: bad date {game.get('date')!r}")
            continue
        if game_date < today and not game.get("result"):
            past_without_result += 1

    if past_without_result:
        logger.warning("%s: %d past game(s) have no result yet",
                        sport_name, past_without_result)
    return (not problems), problems


def write_csv(path, games):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for game in games:
            writer.writerow([game.get(col.lower(), "") for col in CSV_COLUMNS])


def fetch_sport(sport, config):
    """Try each configured source in order. Returns (games, source_name)."""
    for name in sport.get("sources") or DEFAULT_SOURCE_ORDER:
        adapter = SOURCES.get(name)
        if adapter is None:
            logger.warning("%s: unknown source %r", sport["name"], name)
            continue
        try:
            games = adapter.fetch(sport, config=config)
        except Exception as err:  # noqa: BLE001 - fall through to next source
            logger.warning("%s: source %r raised: %s",
                            sport["name"], name, err)
            continue
        if not games:
            continue
        ok, problems = validate(games, sport["name"])
        if not ok:
            logger.warning("%s: source %r failed validation: %s",
                            sport["name"], name, "; ".join(problems[:5]))
            continue
        logger.info("%s: using source %r (%d games)",
                    sport["name"], name, len(games))
        return games, name
    return None, None


def send_alert(email, failures):
    """Email a failure summary via the local mail transfer agent."""
    if not email:
        logger.error("Notifications enabled but no email configured")
        return
    body_lines = ["The Husker schedule fetcher had problems this run:", ""]
    body_lines += [f"  - {name}: {detail}" for name, detail in failures]
    body_lines += ["", "The affected CSV files were left unchanged."]
    message = (f"To: {email}\n"
               f"Subject: [husker-schedules] {len(failures)} item(s) failed\n"
               f"Content-Type: text/plain; charset=utf-8\n\n"
               + "\n".join(body_lines) + "\n")
    for binary in ("/usr/sbin/sendmail", "/bin/sendmail",
                   "/usr/lib/sendmail", "sendmail"):
        try:
            subprocess.run([binary, "-t"], input=message, text=True,
                           check=True, timeout=30)
            logger.info("Alert email sent to %s", email)
            return
        except FileNotFoundError:
            continue
        except Exception as err:  # noqa: BLE001
            logger.error("Alert email via %s failed: %s", binary, err)
            return
    logger.error("No sendmail binary available; alert NOT delivered")


def main():
    setup_logging()
    load_dotenv(BASE_DIR / "config" / ".env")
    config = load_json(BASE_DIR / "config" / "config.json", {})
    sports = load_json(BASE_DIR / "config" / "sports.json",
                       {"sports": []}).get("sports", [])

    output_env = os.getenv("OUTPUT_DIRECTORY")
    output_dir = (Path(output_env) if output_env
                  else BASE_DIR / config.get("output_directory", "output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 64)
    logger.info("Schedule fetch start | %d sports | output=%s",
                len(sports), output_dir)

    failures = []
    updated = 0
    for sport in sports:
        logger.info("-" * 48)
        logger.info("Processing %s", sport["name"])
        games, source = fetch_sport(sport, config)
        if games:
            write_csv(output_dir / sport["filename"], games)
            logger.info("%s: wrote %d games (source: %s)",
                        sport["name"], len(games), source)
            updated += 1
        else:
            logger.error("%s: every source failed; CSV left unchanged",
                          sport["name"])
            failures.append(
                (sport["name"], "all sources failed; CSV left unchanged"))

    try:
        generate_schedule_html(output_dir, sports)
        logger.info("index.html regenerated")
    except Exception as err:  # noqa: BLE001
        logger.error("HTML generation failed: %s", err)
        failures.append(("index.html", f"generation failed: {err}"))

    logger.info("=" * 64)
    logger.info("Schedule fetch done | %d/%d sports updated | %d failure(s)",
                updated, len(sports), len(failures))

    if failures:
        if config.get("enable_notifications"):
            send_alert(config.get("notification_email"), failures)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as fatal:  # noqa: BLE001
        logging.getLogger("husker_schedules").exception(
            "Fatal error: %s", fatal)
        sys.exit(1)
