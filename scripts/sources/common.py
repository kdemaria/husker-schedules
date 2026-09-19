"""Shared helpers for schedule source adapters."""
import datetime
import logging
import re
import time
from zoneinfo import ZoneInfo

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

# The chapter is in Washington state, so every published time is shown in
# Pacific regardless of the zone the source printed it in.
PACIFIC = ZoneInfo("America/Los_Angeles")

# Zone abbreviations the sources print, mapped to real zones. The printed
# abbreviation only picks the region; the game's date decides whether daylight
# time applies, so a source that mislabels CST as CDT still converts correctly.
SOURCE_ZONES = {
    "ET": "America/New_York", "EDT": "America/New_York",
    "EST": "America/New_York",
    "CT": "America/Chicago", "CDT": "America/Chicago",
    "CST": "America/Chicago",
    "MT": "America/Denver", "MDT": "America/Denver",
    "MST": "America/Denver",
    "PT": "America/Los_Angeles", "PDT": "America/Los_Angeles",
    "PST": "America/Los_Angeles",
}

TIME_WITH_ZONE = re.compile(
    r"^\s*(\d{1,2}):(\d{2})\s*([AaPp])\.?[Mm]\.?\s+([A-Za-z]{2,4})\s*$")


def format_pacific(moment):
    """A timezone-aware datetime as "4:15 PM PDT", no leading zero."""
    return (moment.astimezone(PACIFIC).strftime("%I:%M %p").lstrip("0")
            + " " + moment.astimezone(PACIFIC).tzname())


def to_pacific(time_text, date_text):
    """Convert a printed clock time to Pacific: "6:15 PM CDT" -> "4:15 PM PDT".

    Returns the text unchanged when there is nothing safe to convert: a blank,
    a "TBD", a placeholder like "4 or 8 PM", an unparseable date, or a zone we
    do not recognize. Showing a source's own time is better than showing a
    confidently wrong one two hours off.
    """
    match = TIME_WITH_ZONE.match(time_text or "")
    if not match:
        return time_text
    zone_name = SOURCE_ZONES.get(match.group(4).upper())
    if not zone_name:
        logger.info("time %r has an unrecognized zone; leaving as-is",
                    time_text)
        return time_text
    try:
        date = datetime.datetime.strptime(date_text, "%m/%d/%Y").date()
    except (TypeError, ValueError):
        return time_text

    hour = int(match.group(1)) % 12
    if match.group(3).lower() == "p":
        hour += 12
    local = datetime.datetime(date.year, date.month, date.day, hour,
                              int(match.group(2)),
                              tzinfo=ZoneInfo(zone_name))
    pacific = local.astimezone(PACIFIC)
    if pacific.date() != date:
        # Converting would put the time on a different calendar day than the
        # Date column, which reads as an error. Only a pre-2am start could do
        # this, so leave it rather than print a contradiction.
        logger.warning("time %r on %s lands on another day in Pacific; "
                       "leaving as-is", time_text, date_text)
        return time_text
    return format_pacific(pacific)


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
        except requests.HTTPError as err:
            # A 4xx is the server's settled answer (a 404 for an unpublished
            # schedule page, a 403 for a blocked host). Retrying only burns
            # seconds, so fail fast and let the caller try the next URL or
            # the next source. 408/425/429 are the transient exceptions.
            status = getattr(err.response, "status_code", None)
            if status and 400 <= status < 500 and status not in (408, 425, 429):
                logger.warning("GET %s failed: %s (not retrying)", url, err)
                raise
            last_err = err
            logger.warning("GET %s failed (attempt %d/%d): %s",
                           url, attempt + 1, retries + 1, err)
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
        except Exception as err:  # noqa: BLE001 - retry on any transport error
            last_err = err
            logger.warning("GET %s failed (attempt %d/%d): %s",
                           url, attempt + 1, retries + 1, err)
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
    raise last_err
