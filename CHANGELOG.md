# Changelog

## 2025-10-29 - Refactor to Separate Sport Requests

### Breaking Changes
- The application now processes each sport in a separate API request instead of fetching all sports in a single request
- The original `prompt-schedule-getter.txt` is no longer used by the application (kept for reference)

### New Features
- **Sport-Specific Processing**: Each sport is now fetched individually using `prompt-sport-template.txt`
- **Separate HTML Generation**: HTML page is built from CSV files after all sports are fetched using `prompt-html-generator.txt`
- **Sports Configuration**: Sports list is now configurable via `config/sports.json`
- **Environment Variable Support**: Output directory can now be configured via `OUTPUT_DIRECTORY` environment variable in `.env`

### New Files
- `config/sports.json` - Configurable list of sports to fetch
- `prompt-sport-template.txt` - Template for individual sport requests
- `prompt-html-generator.txt` - Template for HTML page generation

### Modified Files
- `scripts/schedule_fetcher.py` - Completely refactored to support per-sport requests
  - Added `_load_sports_config()` method to load sports from JSON
  - Added `_read_prompt_template()` method to support template-based prompts
  - Added `_fetch_sport_schedule()` method to fetch individual sport schedules
  - Added `_generate_html_page()` method to build HTML from CSV files
  - Updated `run()` method to orchestrate separate sport fetches
  - Added support for `OUTPUT_DIRECTORY` environment variable
- `config/.env.example` - Removed Google Drive references, added `OUTPUT_DIRECTORY` variable

### Improvements
- Better error handling for individual sport failures
- More granular logging for each sport
- Configurable sports list without code changes
- Flexible output directory configuration
- Rate limit protection with delays between API calls

### Migration Guide

#### For Existing Users
1. Update your `.env` file to match the new `.env.example` format
2. (Optional) Customize `config/sports.json` to add/remove sports
3. The old `prompt-schedule-getter.txt` is no longer used but kept for reference

#### To Use Custom Output Directory
Add to your `.env` file:
```
OUTPUT_DIRECTORY=/your/custom/path
```

#### To Add/Remove Sports
Edit `config/sports.json` and add/remove entries:
```json
{
  "sports": [
    {
      "name": "Football",
      "filename": "Football.csv"
    }
  ]
}
```

### Technical Details
- Each sport now makes a separate Claude API call with web search enabled
- HTML generation happens after all sports are complete
- 2-second delay between sport requests to avoid rate limits
- Sports are processed sequentially, not in parallel
- Output directory resolution order:
  1. `OUTPUT_DIRECTORY` environment variable
  2. `output_directory` in `config.json`
  3. Default: `output/` in project root
