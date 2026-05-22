"""Shared helpers for schedule source adapters."""
import logging
import time

import requests

logger = logging.getLogger("husker_schedules.sources")

# The CSV column order consumed by html_generator.py and the Google Sheet.
# Do not change without updating both downstream consumers.
CSV_COLUMNS = ["Date", "Day", "Opponent", "Location", "Venue",
               "Time", "Event", "Watch", "Result"]

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

WEEKDAYS = {d: i for i, d in enumerate(
    ["monday", "tuesday", "wednesday", "thursday",
     "friday", "saturday", "sunday"])}

FULL_WEEKDAY = ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"]

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0 Safari/537.36")


def empty_game():
    """A game dict with every CSV column present and blank."""
    return {c.lower(): "" for c in CSV_COLUMNS}


def http_get(url, timeout=30, retries=2, headers=None):
    """GET a URL with a browser UA and simple retry. Returns the response."""
    hdrs = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json"}
    if headers:
        hdrs.update(headers)
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=hdrs, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as err:  # noqa: BLE001 - retry on any transport error
            last_err = err
            logger.warning("GET %s failed (attempt %d/%d): %s",
                           url, attempt + 1, retries + 1, err)
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
    raise last_err
