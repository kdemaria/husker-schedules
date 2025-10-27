# Output Directory

This directory contains the generated Nebraska Huskers schedule files.

## Web Access Setup

To make these files accessible via HTTP/HTTPS for Google Sheets integration, you have several options:

### Option 1: Apache Web Server

1. Create a symlink in your web root:
   ```bash
   sudo ln -s /path/to/husker-schedules/output /var/www/html/schedules
   ```

2. Ensure Apache has read permissions:
   ```bash
   sudo chmod 755 /path/to/husker-schedules/output
   sudo chmod 644 /path/to/husker-schedules/output/*
   ```

3. Files will be accessible at: `http://your-domain.com/schedules/`

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

### Option 3: Python HTTP Server (Development Only)

For testing purposes only:
```bash
cd /path/to/husker-schedules/output
python3 -m http.server 8000
```

Access files at: `http://localhost:8000/`

### Option 4: Google Drive Sync

If syncing to Google Drive:

1. Install rclone or use Google Drive desktop client
2. Configure sync from this directory to your Google Drive
3. Share the files publicly or with specific users
4. Use Google Drive's share URLs in Google Sheets

## File Access URLs

Once configured, access files using:
- Football schedule: `http://your-domain.com/schedules/Football.csv`
- Baseball schedule: `http://your-domain.com/schedules/Baseball.csv`
- Softball schedule: `http://your-domain.com/schedules/Softball.csv`
- Men's Basketball: `http://your-domain.com/schedules/MensBasketball.csv`
- Women's Basketball: `http://your-domain.com/schedules/WomensBasketball.csv`
- Volleyball schedule: `http://your-domain.com/schedules/Volleyball.csv`
- HTML view: `http://your-domain.com/schedules/index.html` (or similar)

## Google Sheets Integration

In Google Sheets, use the IMPORTDATA function:
```
=IMPORTDATA("http://your-domain.com/schedules/Football.csv")
```

Or use Google Apps Script for more advanced integration.
