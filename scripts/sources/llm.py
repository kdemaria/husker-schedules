"""Source adapter: Claude API with web search (last-resort fallback).

Only used when both huskers.com and ESPN fail for a sport. The model is asked
to return a JSON array of games, which is parsed directly -- no scraping of
markdown code fences.
"""
import json
import logging
import os
import re
from pathlib import Path

import anthropic

from .common import CSV_COLUMNS, empty_game

logger = logging.getLogger("husker_schedules.sources.llm")

PROMPT_FILE = Path(__file__).resolve().parents[2] / "prompt-sport-template.txt"


def _load_prompt(sport_name):
    return PROMPT_FILE.read_text(encoding="utf-8").replace(
        "{{SPORT_NAME}}", sport_name)


def _extract_json_array(text):
    """Pull a JSON array of game objects out of the model's response."""
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    raw = fence.group(1) if fence else None
    if raw is None:
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end > start:
            raw = text[start:end + 1]
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as err:
        logger.warning("llm: could not parse JSON: %s", err)
        return None


def fetch(sport_cfg, config=None, today=None):
    """Fetch a sport's schedule via the Claude API as a last resort."""
    config = config or {}
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("llm: ANTHROPIC_API_KEY not set; skipping fallback")
        return None

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": _load_prompt(sport_cfg["name"])}]

    response = None
    for _ in range(6):  # allow a few server-side web_search pause_turn cycles
        response = client.messages.create(
            model=config.get("model", "claude-sonnet-4-5-20250929"),
            max_tokens=config.get("max_tokens", 16000),
            temperature=config.get("temperature", 1.0),
            tools=[{"type": "web_search_20250305", "name": "web_search",
                    "max_uses": 8}],
            messages=messages,
        )
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})

    text = "".join(block.text for block in response.content
                   if getattr(block, "type", "") == "text")
    rows = _extract_json_array(text)
    if not rows:
        logger.warning("llm: no usable schedule returned for %s",
                       sport_cfg["name"])
        return None

    games = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        game = empty_game()
        for column in CSV_COLUMNS:
            key = column.lower()
            value = row.get(key, row.get(column, ""))
            game[key] = "" if value is None else str(value).strip()
        if game["opponent"] or game["date"]:
            games.append(game)

    logger.info("llm: parsed %d games for %s", len(games), sport_cfg["name"])
    return games or None
