"""Source adapter: huskers.com (the official, canonical schedule source).

huskers.com is a server-rendered Nuxt site. Each game on a sport's schedule
page is a ``.schedule-event-item`` element whose children carry the date,
opponent, location, venue, broadcast and result/time. We parse that rendered
HTML deterministically.

The pages print each game's month, day and weekday but not the year. Years
are inferred afterwards (`_assign_dates`) from the printed weekday plus the
fact that the page lists games in chronological order.

A sport's main schedule page is unpublished between seasons, so `fetch` falls
back to the season-scoped URLs (`_candidate_urls`) rather than failing.
"""
import datetime
import logging
import re

from bs4 import BeautifulSoup

from .common import (FULL_WEEKDAY, MONTHS, WEEKDAYS, empty_game,
                     http_get, to_pacific)

logger = logging.getLogger("husker_schedules.sources.huskers")

SCHEDULE_URL = "https://huskers.com/sports/{slug}/schedule"
# Season-scoped archive. huskers.com unpublishes a sport's main schedule page
# in the gap between one season ending and the next being released (baseball,
# September 2026), but the season URL keeps serving every published season.
SEASON_URL = "https://huskers.com/sports/{slug}/schedule/season/{year}"

# Broadcaster names to recognize in a TV logo's alt text, most specific first.
# huskers.com stopped labelling the TV link, so the only place a network
# survives in the markup is the logo image's alt, which is the raw asset
# filename: "FS1-1040x585", "FOX_small_black", "2560px-CBS_logo_(2020)".
# Matching known names inside it keeps filename noise out of the CSV.
NETWORKS = (
    ("big ten network", "BTN"),
    ("btn", "BTN"),
    ("fs1", "FS1"),
    ("fs2", "FS2"),
    ("fox", "FOX"),
    ("espn+", "ESPN+"),
    ("espnu", "ESPNU"),
    ("espn2", "ESPN2"),
    ("espn", "ESPN"),
    ("abc", "ABC"),
    ("cbs", "CBS"),
    ("peacock", "Peacock"),
    ("nbc", "NBC"),
    ("paramount", "Paramount+"),
)

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


def _parse_watch(item):
    """The game's broadcaster, or "" when none is published yet.

    Prefers a labelled TV link if huskers.com ever restores one, then falls
    back to the network logo's alt text in the game's link row. Returns ""
    rather than guessing when the alt matches no known network, so an
    unrecognized logo leaves the column blank instead of printing a filename.
    """
    label = _text(item.select_one(".schedule-event-item-links__link--tv"))
    if label:
        return label
    images = item.select(".schedule-event-bottom__link img")
    images += item.select("img.schedule-event-item-links__image")
    for image in images:
        alt = (image.get("alt") or "").lower()
        if not alt:
            continue
        for needle, network in NETWORKS:
            if needle in alt:
                return network
    return ""


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

    game["watch"] = _parse_watch(item)
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


def _parse_games(html, sport_cfg, today=None):
    """Parse one rendered schedule page into a list of games."""
    # html.parser is stdlib -- no compiled dependency to install on the host.
    soup = BeautifulSoup(html, "html.parser")

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
    # Times are converted only after _assign_dates, which resolves the year the
    # page omits: the date is what decides daylight vs standard time.
    for game, _month, _day, _weekday in rows:
        game["time"] = to_pacific(game["time"], game["date"])
    return [game for game, _month, _day, _weekday in rows]


def _candidate_urls(slug, today):
    """Schedule URLs to try, newest first.

    The canonical page is correct whenever huskers.com has a current season
    published. When it 404s (offseason, next season not announced yet) the
    season-scoped archive still answers: next season as soon as it is posted,
    otherwise the season just finished.
    """
    yield SCHEDULE_URL.format(slug=slug)
    for year in (today.year + 1, today.year, today.year - 1):
        yield SEASON_URL.format(slug=slug, year=year)


def fetch(sport_cfg, config=None, today=None):
    """Fetch and parse a sport's schedule from huskers.com."""
    slug = sport_cfg.get("huskers_slug")
    if not slug:
        return None
    timeout = (config or {}).get("request_timeout", 30)
    today = today or datetime.date.today()

    for url in _candidate_urls(slug, today):
        try:
            response = http_get(url, timeout=timeout)
        except Exception as err:  # noqa: BLE001 - try the next candidate URL
            logger.warning("huskers: %s unusable for %s: %s",
                           url, sport_cfg["name"], err)
            continue
        games = _parse_games(response.text, sport_cfg, today=today)
        if games:
            logger.info("huskers: parsed %d games for %s from %s",
                        len(games), sport_cfg["name"], url)
            return games
        logger.info("huskers: no games on %s for %s",
                    url, sport_cfg["name"])
    logger.warning("huskers: no schedule page yielded games for %s",
                   sport_cfg["name"])
    return None
