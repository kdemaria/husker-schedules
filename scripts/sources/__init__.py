"""Schedule source adapters.

Each adapter exposes ``fetch(sport_cfg, config=None, today=None)`` and returns
a list of game dicts (keys matching ``common.CSV_COLUMNS`` lowercased), or
``None`` if it could not produce a schedule.
"""
