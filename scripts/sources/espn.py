"""Source adapter: ESPN public site API (fallback for the sports it covers).

ESPN exposes a stable JSON schedule endpoint per team. Nebraska's team id is
per-sport: 158 for football and basketball, 99 for baseball. ESPN has no
public college softball or volleyball league, so those sports omit an "espn"
config block and this adapter returns None for them.
"""
import datetime
import logging
from zoneinfo import ZoneInfo

from .common import FULL_WEEKDAY, empty_game, http_get

logger = logging.getLogger("husker_schedules.sources.espn")

API_URL = ("https://site.api.espn.com/apis/site/v2/sports/{path}/"
           "teams/{team_id}/schedule")
CENTRAL = ZoneInfo("America/Chicago")


def _score(competitor):
    value = competitor.get("score")
    if isinstance(value, dict):
        value = value.get("value", value.get("displayValue"))
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return value


def _broadcast(competition):
    for entry in competition.get("broadcasts") or []:
        names = entry.get("names") or []
        if names:
            return names[0]
        short = (entry.get("media") or {}).get("shortName")
        if short:
            return short
    for entry in competition.get("geoBroadcasts") or []:
        short = (entry.get("media") or {}).get("shortName")
        if short:
            return short
    return ""


def _parse_event(event, team_id):
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    competition = competitions[0]

    nebraska = opponent = None
    for competitor in competition.get("competitors") or []:
        same = str((competitor.get("team") or {}).get("id")) == str(team_id)
        if same:
            nebraska = competitor
        else:
            opponent = competitor
    if not nebraska or not opponent:
        return None

    game = empty_game()
    iso = competition.get("date") or event.get("date") or ""
    local = datetime.datetime.fromisoformat(
        iso.replace("Z", "+00:00")).astimezone(CENTRAL)
    game["date"] = local.strftime("%m/%d/%Y")
    game["day"] = FULL_WEEKDAY[local.weekday()]
    game["time"] = local.strftime("%-I:%M %p") \
        if event.get("timeValid", True) else "TBD"

    opponent_team = opponent.get("team") or {}
    game["opponent"] = (opponent_team.get("location")
                        or opponent_team.get("name")
                        or opponent_team.get("displayName") or "")

    venue = competition.get("venue") or {}
    address = venue.get("address") or {}
    city_state = ", ".join(
        part for part in (address.get("city"), address.get("state")) if part)
    if not competition.get("neutralSite") \
            and nebraska.get("homeAway") == "home":
        game["location"] = "Lincoln NE"
    else:
        game["location"] = city_state
    game["venue"] = venue.get("fullName", "")
    game["watch"] = _broadcast(competition)

    status = (competition.get("status") or {}).get("type") or {}
    if status.get("completed"):
        ours, theirs = _score(nebraska), _score(opponent)
        if ours is not None and theirs is not None:
            outcome = "W" if nebraska.get("winner") else "L"
            game["result"] = f"{outcome} {ours}-{theirs}"

    notes = competition.get("notes") or []
    if notes:
        game["event"] = notes[0].get("headline", "")
    if not game["event"]:
        season_type = (event.get("seasonType") or {}).get("name", "")
        if season_type and season_type.lower() != "regular season":
            game["event"] = season_type
    return game


def fetch(sport_cfg, config=None, today=None):
    """Fetch and parse a sport's schedule from the ESPN site API."""
    espn = sport_cfg.get("espn")
    if not espn:
        return None
    timeout = (config or {}).get("request_timeout", 30)
    today = today or datetime.date.today()

    events = []
    for season in (today.year, today.year + 1, today.year - 1):
        url = API_URL.format(path=espn["path"], team_id=espn["team_id"])
        try:
            data = http_get(f"{url}?season={season}", timeout=timeout).json()
        except Exception as err:  # noqa: BLE001 - try the next season
            logger.warning("espn: season %s failed for %s: %s",
                           season, sport_cfg["name"], err)
            continue
        events = data.get("events") or []
        if events:
            break

    games = []
    for event in events:
        try:
            game = _parse_event(event, espn["team_id"])
        except Exception as err:  # noqa: BLE001 - skip a bad event
            logger.warning("espn: could not parse an event for %s: %s",
                           sport_cfg["name"], err)
            continue
        if game:
            games.append(game)

    logger.info("espn: parsed %d games for %s", len(games), sport_cfg["name"])
    return games or None
