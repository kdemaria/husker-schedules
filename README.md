# Nebraska Huskers Schedule Fetcher

An automated system for fetching and maintaining Nebraska Cornhuskers sports schedules using the Claude AI API. This tool generates up-to-date CSV and HTML schedules for multiple sports and makes them available for integration with Google Sheets and other tools.

## Features

- **Automated Schedule Generation**: Uses Claude AI (Sonnet 4.5) to fetch current schedules for 6 sports
- **Multiple Sports Coverage**: Football, Baseball, Softball, Men's Basketball, Women's Basketball, and Volleyball
- **CSV & HTML Output**: Generates both machine-readable CSV files and human-readable HTML schedules
- **Web-Accessible**: Files can be served via HTTP/HTTPS for Google Sheets integration
- **Scheduled Execution**: Run automatically via cron jobs
- **Secure Credential Management**: API keys stored in environment variables
- **Comprehensive Logging**: Detailed logs for monitoring and debugging
- **Automatic Cleanup**: Removes old temporary files automatically

## Sports Covered

1. Football
2. Baseball
3. Softball
4. Men's Basketball
5. Women's Basketball
6. Volleyball

## Project Structure

```
husker-schedules/
├── README.md                          # This file
├── prompt-schedule-getter.txt         # Prompt for Claude AI
├── requirements.txt                   # Python dependencies
├── setup.sh                          # Setup script
├── .gitignore                        # Git ignore rules
├── config/
│   ├── .env.example                  # Environment variables template
│   ├── .env                          # Your API keys (not tracked in git)
│   ├── config.json.example           # Configuration template
│   └── config.json                   # Your configuration (created on setup)
├── scripts/
│   └── schedule_fetcher.py           # Main Python script
├── tmp/                              # Temporary files (auto-cleaned)
├── output/                           # Generated schedules (web-accessible)
│   ├── README.md                     # Web access setup instructions
│   └── .htaccess                     # Apache configuration
└── logs/                             # Application logs
```

## Requirements

- Python 3.8 or higher
- pip (Python package manager)
- An Anthropic API key (get one at https://console.anthropic.com/settings/keys)
- (Optional) Web server (Apache/Nginx) for serving files
- (Optional) Google Drive for cloud storage

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd husker-schedules
```

### 2. Run the Setup Script

```bash
./setup.sh
```

This script will:
- Create a Python virtual environment
- Install required dependencies
- Create necessary directories
- Generate configuration files from templates
- Set up proper permissions

### 3. Configure Your API Key

Edit `config/.env` and add your Anthropic API key:

```bash
nano config/.env
```

```env
ANTHROPIC_API_KEY=your_actual_api_key_here
```

### 4. (Optional) Customize Configuration

Edit `config/config.json` to customize settings:

```json
{
  "model": "claude-sonnet-4-5-20241022",
  "max_tokens": 8000,
  "temperature": 1.0,
  "output_directory": "output",
  "cleanup_days": 7
}
```

## Usage

### Manual Execution

Activate the virtual environment and run the script:

```bash
source venv/bin/activate
python3 scripts/schedule_fetcher.py
```

### Automated Execution with Cron

To run the script automatically, set up a cron job:

1. Edit your crontab:
   ```bash
   crontab -e
   ```

2. Add one of these lines depending on your desired schedule:

   **Run daily at 6:00 AM:**
   ```cron
   0 6 * * * cd /path/to/husker-schedules && /path/to/husker-schedules/venv/bin/python3 /path/to/husker-schedules/scripts/schedule_fetcher.py >> /path/to/husker-schedules/logs/cron.log 2>&1
   ```

   **Run twice daily (6 AM and 6 PM):**
   ```cron
   0 6,18 * * * cd /path/to/husker-schedules && /path/to/husker-schedules/venv/bin/python3 /path/to/husker-schedules/scripts/schedule_fetcher.py >> /path/to/husker-schedules/logs/cron.log 2>&1
   ```

   **Run every Monday at 8:00 AM:**
   ```cron
   0 8 * * 1 cd /path/to/husker-schedules && /path/to/husker-schedules/venv/bin/python3 /path/to/husker-schedules/scripts/schedule_fetcher.py >> /path/to/husker-schedules/logs/cron.log 2>&1
   ```

3. Replace `/path/to/husker-schedules` with the actual path to your installation.

### Cron Schedule Helper

```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sunday = 0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

Examples:
- `0 6 * * *` - Every day at 6:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 8 * * 1` - Every Monday at 8:00 AM
- `0 6,18 * * *` - Every day at 6 AM and 6 PM

## Web Access Setup

To make the schedule files accessible via HTTP/HTTPS for Google Sheets integration:

### Option 1: Apache Web Server

1. Create a symlink in your web root:
   ```bash
   sudo ln -s /path/to/husker-schedules/output /var/www/html/schedules
   ```

2. Ensure proper permissions:
   ```bash
   sudo chmod 755 /path/to/husker-schedules/output
   sudo chmod 644 /path/to/husker-schedules/output/*
   ```

3. Access files at: `http://your-domain.com/schedules/`

The included `.htaccess` file in the `output` directory enables CORS headers for Google Sheets access.

### Option 2: Nginx Web Server

Add this to your Nginx configuration:

```nginx
location /schedules {
    alias /path/to/husker-schedules/output;
    autoindex on;
    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods 'GET, OPTIONS';
}
```

Then reload Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Option 3: Google Drive Sync

Use `rclone` or Google Drive Desktop to sync the output directory:

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure Google Drive
rclone config

# Sync output directory to Google Drive
rclone sync /path/to/husker-schedules/output remote:husker-schedules
```

See `output/README.md` for more detailed web access instructions.

## Google Sheets Integration

Once files are web-accessible, you can import them into Google Sheets:

### Method 1: IMPORTDATA Function

```
=IMPORTDATA("http://your-domain.com/schedules/Football.csv")
```

### Method 2: Google Apps Script

For more control, use Apps Script:

```javascript
function importSchedule() {
  var url = "http://your-domain.com/schedules/Football.csv";
  var response = UrlFetchApp.fetch(url);
  var csv = response.getContentText();
  var data = Utilities.parseCsv(csv);

  var sheet = SpreadsheetApp.getActiveSheet();
  sheet.getRange(1, 1, data.length, data[0].length).setValues(data);
}
```

## Output Files

The script generates the following files in the `output/` directory:

- `Football.csv` - Football schedule
- `Baseball.csv` - Baseball schedule
- `Softball.csv` - Softball schedule
- `MensBasketball.csv` - Men's Basketball schedule
- `WomensBasketball.csv` - Women's Basketball schedule
- `Volleyball.csv` - Volleyball schedule
- `index.html` - HTML document with all schedules (Nebraska-branded)
- `scheduled-sources.zip` - Compressed archive of all files

### CSV Format

Each CSV file contains the following columns:

```
Date, Day, Opponent, Home/Away, Location, Venue, Time, Event, Result
```

Example:
```csv
Date,Day,Opponent,Home/Away,Location,Venue,Time,Event,Result
2025-09-06,Sat,Minnesota,Home,Lincoln,Memorial Stadium,11:00 AM,Regular Season,W 24-17
```

## Logging

Logs are stored in the `logs/` directory:

- `schedule_fetcher_YYYYMMDD.log` - Daily log files
- `cron.log` - Cron job output (if configured)

View recent logs:
```bash
tail -f logs/schedule_fetcher_$(date +%Y%m%d).log
```

## Troubleshooting

### API Key Issues

If you get authentication errors:
1. Verify your API key in `config/.env`
2. Check your API key is active at https://console.anthropic.com/settings/keys
3. Ensure you have sufficient API credits

### Permission Issues

If the script can't write files:
```bash
chmod 755 output/
chmod 755 logs/
chmod 755 tmp/
```

### Cron Job Not Running

1. Check cron is running: `systemctl status cron`
2. Check cron logs: `grep CRON /var/log/syslog`
3. Verify paths in crontab are absolute paths
4. Check the `logs/cron.log` file for errors

### Web Access Issues

1. Check file permissions: `ls -la output/`
2. Verify web server configuration
3. Check web server error logs
4. Test CORS headers: `curl -I http://your-domain.com/schedules/Football.csv`

## Security Considerations

- **API Keys**: Never commit `config/.env` to version control (it's in `.gitignore`)
- **File Permissions**: Ensure output files have appropriate read permissions but not write permissions for the web server
- **CORS**: The `.htaccess` file enables CORS - adjust if you want to restrict access to specific domains
- **HTTPS**: Use HTTPS for production to encrypt data in transit

## Updating

To update the script:

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## Maintenance

### Clean Old Logs

```bash
find logs/ -name "*.log" -mtime +30 -delete
```

### Check Disk Space

```bash
du -sh output/ tmp/ logs/
```

### Backup Configuration

```bash
tar -czf husker-schedules-backup.tar.gz config/.env config/config.json
```

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review this README and `output/README.md`
3. Verify your configuration in `config/`
4. Check the Anthropic API status

## License

[Add your license here]

## Credits

Created for the University of Nebraska Athletic Department schedule management.

Uses Claude AI by Anthropic for intelligent schedule gathering and formatting.
