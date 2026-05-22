# Handoff — husker-schedules

`husker-schedules` fetches University of Nebraska sports schedules and writes
the CSV files that wacornhuskers.com displays.

## Current state (rebuilt 2026-05-22)

The project no longer uses the Claude API to *scrape* schedules.
`schedule_fetcher.py` was rewritten as a source-adapter design
(`scripts/sources/`):

- **huskers.com** — HTML parsing of the official schedule pages. Primary
  source, covers all 6 sports.
- **ESPN** — public JSON API. Fallback for football, basketball, baseball.
- **Claude API** — last-resort fallback only.

First source that returns a valid schedule wins. Every result is validated
before its CSV is written; on failure the previous CSV is kept and an email
alert is sent to ken@demaria.net.

> `README.md` and `CHANGELOG.md` predate this rewrite and describe the old
> LLM-scraping design. Treat them as out of date.

## Runtime

- Runs as a **nightly SiteGround cron, 03:00 UTC** (`0 3 * * *`), from the
  server clone at `/home/customer/scripts/husker-schedules`.
- Output goes to `OUTPUT_DIRECTORY` (in `config/.env`), currently the
  wacornhuskers.com `public_html/wp-content/uploads/husker-schedules/`
  folder. The site's `wch-husker-schedules` mu-plugin reads the CSVs there.
- Deploy: edit on Mac → push to GitHub → `git pull` in the server clone.

## Open item

Rotate the `ANTHROPIC_API_KEY` in `config/.env` — it was exposed in a chat
session. The LLM path is now only a rare fallback, so this is low-urgency.

## Full context

The cross-project handoff doc, covering both this repo and the WordPress
side, lives in the wacornhuskers-site repo:
`wacornhuskers-site/handoff/husker-schedules-rebuild.md`.
