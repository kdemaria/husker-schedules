"""Source adapter: huskers.com (the official, canonical schedule source).

huskers.com is a server-rendered Nuxt site. Each game on a sport's schedule
page is a ``.schedule-event-item`` element whose children carry the date,
opponent, location, venue, broadcast and result/time. We parse that rendered
HTML deterministically.

The pages print each game's month, day and weekday but not the year. Years
are inferred afterwards (`_assign_dates`) from the printed weekday plus the
fact that the page lists games in chronological order.
"""
import datetime
import logging
import re

from bs4 import BeautifulSoup

from .common import FULL_WEEKDAY, MONTHS, WEEKDAYS, empty_game, http_get

logger = logging.getLogger("husker_schedules.sources.huskers")

SCHEDULE_URL = "https://huskers.com/sports/{slug}/schedule"

# Ceremony / fan-event rows that the schedule pages mix in with real games.
# None of these phrases ever appears in an actual opponent's name.
NON_GAME_KEYWORDS = (
    "presented by", "media day", "selection show", "selection sunday",
    "spring game", "pro day", "fan day", "fan fest", "fanfest",
)


def _text(node):
    return node.get_text(" ", strip=True) if node else ""


def _parse_date(item):
    """Return (month, day, weekday_name) for a schedule item, or None."""
    weekday = ""
    label = ""
    for tag in item.select(".schedule-event-date time"):
        classes = tag.get("class") or []
        if "schedule-event-date__label" in classes:
            label = tag.get_text(strip=True)
        elif not weekday:
            weekday = tag.get_text(strip=True)
    if not label:
        label = _text(item.select_one(".schedule-event-date__label"))
    match = re.match(r"([A-Za-z]+)\.?\s+(\d{1,2})", label)
    if not match:
        return None
    month = MONTHS.get(match.group(1)[:3].lower())
    if not month:
        return None
    return month, int(match.group(2)), weekday


def _parse_result_or_time(item):
    """Return (result, time).

    The result slot is dual-purpose: a final result for completed games,
    otherwise the scheduled start time (or "TBA").
    """
    text = _text(item.select_one(".schedule-event-item-result__label"))
    win = item.select_one(".schedule-event-item-result__win")
    loss = item.select_one(".schedule-event-item-result__loss")
    if win or loss:
        outcome = "W" if win else "L"
        score = re.search(r"\d+\s*-\s*\d+", text)
        result = (f"{outcome} {score.group(0).replace(' ', '')}"
                  if score else outcome)
        return result, ""
    if re.search(r"\d", text) and re.search(r"[AP]M", text, re.I):
        return "", text
    if text.upper() in ("", "TBA", "TBD"):
        return "", "TBD"
    return "", text  # e.g. "Postponed" / "Canceled"


def _parse_item(item):
    """Parse one schedule item into (game, divider, month, day, weekday).

    Date/Day are filled in later by `_assign_dates`. Returns None if the item
    carries no usable date.
    """
    parsed_date = _parse_date(item)
    if not parsed_date:
        return None
    month, day, weekday = parsed_date

    game = empty_game()
    game["opponent"] = _text(
        item.select_one(".schedule-event-item-default__opponent-name"))
    divider = _text(
        item.select_one(".schedule-event-item-default__divider"))

    venue_type = _text(item.select_one(".schedule-event-venue__type-label"))
    location_raw = _text(item.select_one(".schedule-event-location"))
    city, venue = location_raw, ""
    if " / " in location_raw:
        city, venue = (part.strip()
                       for part in location_raw.split(" / ", 1))
    if venue_type.lower() == "home":
        game["location"] = "Lincoln NE"
        game["venue"] = venue or city
    else:
        game["location"] = city
        game["venue"] = venue

    game["watch"] = _text(
        item.select_one(".schedule-event-item-links__link--tv"))
    game["event"] = _text(
        item.select_one(".schedule-event-item-default__promo-title"))
    game["result"], game["time"] = _parse_result_or_time(item)
    return game, divider, month, day, weekday


def _is_non_game(game, divider):
    """True for ceremony/event rows rather than competitions.

    Real games always carry a "vs."/"at" divider; most events lack one. A few
    events mimic a game's markup, so a keyword check on the title backs up the
    structural check.
    """
    opponent = game["opponent"].lower()
    if opponent in ("huskers", "nebraska", ""):
        return True
    if not divider:
        return True
    haystack = opponent + " " + game["event"].lower()
    return any(keyword in haystack for keyword in NON_GAME_KEYWORDS)


def _choose_year(month, day, weekday, prev_date, today):
    """Pick the calendar year for a month/day.

    The printed weekday usually identifies the year uniquely, but placeholder
    rows can carry a stale weekday -- so the choice must also keep the
    schedule in chronological order with the preceding game.
    """
    target = WEEKDAYS.get((weekday or "").strip().lower())
    candidates = []
    for year in range(today.year - 1, today.year + 3):
        try:
            date = datetime.date(year, month, day)
        except ValueError:
            continue
        weekday_ok = target is None or date.weekday() == target
        monotonic_ok = prev_date is None or date >= prev_date
        candidates.append((date, weekday_ok, monotonic_ok))

    reference = prev_date or today
    for need_monotonic in (True, False):
        for need_weekday in (True, False):
            picks = [date for date, weekday_ok, monotonic_ok in candidates
                     if (monotonic_ok or not need_monotonic)
                     and (weekday_ok or not need_weekday)]
            if picks:
                return min(
                    picks, key=lambda d: abs((d - reference).days)).year
    return today.year


def _assign_dates(rows, today=None):
    """Fill Date/Day on each game, resolving the page-omitted year.

    ``rows`` is a list of (game, month, day, weekday) tuples in page order;
    huskers.com lists games chronologically.
    """
    today = today or datetime.date.today()
    prev_date = None
    for game, month, day, weekday in rows:
        year = _choose_year(month, day, weekday, prev_date, today)
        date = datetime.date(year, month, day)
        game["date"] = f"{month:02d}/{day:02d}/{year}"
        # Derive Day from the resolved date so Date and Day always agree
        # (a placeholder row's printed weekday can be stale).
        game["day"] = FULL_WEEKDAY[date.weekday()]
        prev_date = date


def fetch(sport_cfg, config=None, today=None):
    """Fetch and parse a sport's schedule from huskers.com."""
    slug = sport_cfg.get("huskers_slug")
    if not slug:
        return None
    url = SCHEDULE_URL.format(slug=slug)
    timeout = (config or {}).get("request_timeout", 30)
    response = http_get(url, timeout=timeout)
    # html.parser is stdlib -- no compiled dependency to install on the host.
    soup = BeautifulSoup(response.text, "html.parser")

    rows = []
    for item in soup.select(".schedule-event-item"):
        try:
            parsed = _parse_item(item)
        except Exception as err:  # noqa: BLE001 - skip a bad row, keep going
            logger.warning("huskers: could not parse an item for %s: %s",
                           sport_cfg["name"], err)
            continue
        if not parsed:
            continue
        game, divider, month, day, weekday = parsed
        if _is_non_game(game, divider):
            logger.info("huskers: skipping non-game row (%r) for %s",
                        game["opponent"], sport_cfg["name"])
            continue
        rows.append((game, month, day, weekday))

    _assign_dates(rows, today=today)
    games = [game for game, _month, _day, _weekday in rows]
    logger.info("huskers: parsed %d games for %s",
                len(games), sport_cfg["name"])
    return games or None
