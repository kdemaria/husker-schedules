#!/usr/bin/env python3
"""
Test script to verify season blackout logic
"""

from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
from pathlib import Path


def is_sport_in_blackout(sport, test_date=None):
    """
    Test the blackout period logic.

    Args:
        sport: Sport dict with season_end_month and season_end_day
        test_date: Date to test (defaults to today)

    Returns:
        True if in blackout, False otherwise
    """
    if 'season_end_month' not in sport or 'season_end_day' not in sport:
        return False

    today = test_date.date() if test_date else datetime.now().date()
    current_year = today.year

    # Calculate season end date for current year
    season_end = datetime(
        current_year,
        sport['season_end_month'],
        sport['season_end_day']
    ).date()

    # If season end is in the future this year, check last year's end
    if season_end > today:
        season_end = datetime(
            current_year - 1,
            sport['season_end_month'],
            sport['season_end_day']
        ).date()

    # Calculate blackout end (3 months after season end)
    blackout_end = season_end + relativedelta(months=3)

    # Check if we're in the blackout period
    in_blackout = season_end < today <= blackout_end

    return in_blackout, season_end, blackout_end


def main():
    # Load sports config
    sports_config_path = Path(__file__).parent.parent / "config" / "sports.json"
    with open(sports_config_path, 'r') as f:
        config = json.load(f)
        sports = config.get('sports', [])

    today = datetime.now()

    print("=" * 70)
    print(f"Season Blackout Period Test - {today.strftime('%B %d, %Y')}")
    print("=" * 70)
    print()

    for sport in sports:
        in_blackout, season_end, blackout_end = is_sport_in_blackout(sport)

        status = "🔴 SKIP (in blackout)" if in_blackout else "✅ UPDATE"

        print(f"{sport['name']:20s} {status}")
        print(f"  Season ends:    {season_end.strftime('%B %d, %Y')}")
        print(f"  Blackout ends:  {blackout_end.strftime('%B %d, %Y')}")

        if in_blackout:
            days_until_update = (blackout_end - today.date()).days
            print(f"  Resume updates: in {days_until_update} days")

        print()

    print("=" * 70)
    print("How it works:")
    print("  ✅ UPDATE = Currently in season OR 3+ months after season end")
    print("  🔴 SKIP   = Within 3 months after season end (blackout period)")
    print("=" * 70)


if __name__ == "__main__":
    main()
