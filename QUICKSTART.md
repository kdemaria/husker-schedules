# Quick Start Guide

Get the Nebraska Huskers Schedule Fetcher up and running in 5 minutes.

## Prerequisites

- Linux server with internet access
- Python 3.8+ installed
- An Anthropic API key ([Get one here](https://console.anthropic.com/settings/keys))

## Installation (5 steps)

### 1. Clone and Enter Directory

```bash
git clone <repository-url>
cd husker-schedules
```

### 2. Run Setup Script

```bash
./setup.sh
```

This creates the virtual environment and installs all dependencies.

### 3. Configure API Key

```bash
nano config/.env
```

Add your API key:
```env
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

Save and exit (Ctrl+X, then Y, then Enter).

### 4. Test the Script

```bash
source venv/bin/activate
python3 scripts/schedule_fetcher.py
```

You should see logs indicating the script is running. Output files will be in the `output/` directory.

### 5. Set Up Cron (Optional)

To run automatically daily at 6 AM:

```bash
crontab -e
```

Add this line (replace `/path/to/husker-schedules` with actual path):

```cron
0 6 * * * cd /path/to/husker-schedules && /path/to/husker-schedules/venv/bin/python3 /path/to/husker-schedules/scripts/schedule_fetcher.py >> /path/to/husker-schedules/logs/cron.log 2>&1
```

To find your actual path:
```bash
pwd
```

## Making Files Web-Accessible

### Option A: Apache

```bash
# Create symlink in web root
sudo ln -s /path/to/husker-schedules/output /var/www/html/schedules

# Set permissions
sudo chmod 755 /path/to/husker-schedules/output

# Access at: http://your-domain.com/schedules/
```

### Option B: Simple HTTP Server (Testing Only)

```bash
cd output
python3 -m http.server 8000
# Access at: http://your-server-ip:8000/
```

### Option C: Google Drive Sync

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure
rclone config

# Sync
rclone sync /path/to/husker-schedules/output remote:husker-schedules
```

## Using with Google Sheets

Once files are web-accessible, in Google Sheets use:

```
=IMPORTDATA("http://your-domain.com/schedules/Football.csv")
```

## Troubleshooting

**Script fails with API error:**
- Check your API key in `config/.env`
- Verify you have API credits at https://console.anthropic.com/

**Permission errors:**
```bash
chmod 755 output/ logs/ tmp/
```

**Cron not running:**
- Check cron is active: `sudo systemctl status cron`
- View logs: `tail -f logs/cron.log`

## Next Steps

- Read the full [README.md](README.md) for detailed information
- See [CRON_SETUP.md](CRON_SETUP.md) for advanced scheduling
- Check `output/README.md` for web server configuration details

## Quick Command Reference

```bash
# Activate environment
source venv/bin/activate

# Run manually
python3 scripts/schedule_fetcher.py

# View logs
tail -f logs/schedule_fetcher_$(date +%Y%m%d).log

# Check output files
ls -lh output/

# View cron jobs
crontab -l

# Edit cron jobs
crontab -e
```

## Expected Output Files

After running successfully, you should see these files in `output/`:

- Football.csv
- Baseball.csv
- Softball.csv
- MensBasketball.csv
- WomensBasketball.csv
- Volleyball.csv
- index.html (Nebraska-branded schedule view)
- scheduled-sources.zip (archive of all files)

## Support

For detailed documentation, see [README.md](README.md).

For cron setup help, see [CRON_SETUP.md](CRON_SETUP.md).

For web access setup, see `output/README.md`.
