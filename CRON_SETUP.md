# Cron Setup Guide

This guide provides detailed instructions for setting up automated execution of the Nebraska Huskers Schedule Fetcher using cron.

## Quick Start

1. Open your crontab editor:
   ```bash
   crontab -e
   ```

2. Add one of the example schedules below (adjust the path):
   ```cron
   0 6 * * * cd /path/to/husker-schedules && /path/to/husker-schedules/venv/bin/python3 /path/to/husker-schedules/scripts/schedule_fetcher.py >> /path/to/husker-schedules/logs/cron.log 2>&1
   ```

3. Save and exit. Cron will automatically pick up the changes.

## Understanding Cron Syntax

```
* * * * * command to execute
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sunday = 0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### Special Characters

- `*` - Any value (every)
- `,` - List of values (e.g., `1,15` = 1st and 15th)
- `-` - Range of values (e.g., `1-5` = 1 through 5)
- `/` - Step values (e.g., `*/2` = every 2)

## Common Schedules

### Daily Schedules

**Every day at 6:00 AM:**
```cron
0 6 * * * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

**Every day at midnight:**
```cron
0 0 * * * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

**Twice daily (6 AM and 6 PM):**
```cron
0 6,18 * * * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

**Every 6 hours:**
```cron
0 */6 * * * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

**Every 4 hours during business hours (8 AM - 8 PM):**
```cron
0 8-20/4 * * * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

### Weekly Schedules

**Every Monday at 8:00 AM:**
```cron
0 8 * * 1 cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

**Every Sunday at 10:00 PM:**
```cron
0 22 * * 0 cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

**Weekdays at 7:00 AM (Monday-Friday):**
```cron
0 7 * * 1-5 cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

### During Sports Seasons

**During football season (September-December), twice daily:**
```cron
0 6,18 * 9-12 * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

**During basketball season (November-March), daily at 7 AM:**
```cron
0 7 * 11-12,1-3 * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

## Complete Cron Entry Template

Here's a complete cron entry with all necessary components:

```cron
# Nebraska Huskers Schedule Fetcher - Runs daily at 6 AM
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

0 6 * * * cd /absolute/path/to/husker-schedules && /absolute/path/to/husker-schedules/venv/bin/python3 /absolute/path/to/husker-schedules/scripts/schedule_fetcher.py >> /absolute/path/to/husker-schedules/logs/cron.log 2>&1
```

## Important Notes

### Use Absolute Paths

Always use absolute paths in cron jobs. To find the absolute path:

```bash
cd /path/to/husker-schedules
pwd
```

### Test Before Scheduling

Test your cron command manually first:

```bash
cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py
```

### Environment Variables

Cron runs with a minimal environment. If your script needs specific environment variables, you can:

1. **Set them in crontab:**
   ```cron
   ANTHROPIC_API_KEY=your_key_here
   0 6 * * * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
   ```

2. **Or ensure your `.env` file is being loaded** (already handled by the script)

### Logging

The `>> logs/cron.log 2>&1` part means:
- `>>` - Append to file (use `>` to overwrite)
- `logs/cron.log` - Output file location
- `2>&1` - Redirect errors (stderr) to the same file as output (stdout)

## Managing Cron Jobs

### View Current Cron Jobs

```bash
crontab -l
```

### Edit Cron Jobs

```bash
crontab -e
```

### Remove All Cron Jobs

```bash
crontab -r
```

### Remove Specific Job

```bash
crontab -e
# Delete the line you want to remove, then save
```

## Monitoring Cron Jobs

### Check if Cron is Running

```bash
systemctl status cron
# or on some systems:
systemctl status crond
```

### View Cron Logs (System)

```bash
# On Ubuntu/Debian:
grep CRON /var/log/syslog

# On CentOS/RHEL:
grep CRON /var/log/cron

# Recent entries:
tail -f /var/log/syslog | grep CRON
```

### View Application Logs

```bash
# View today's log:
tail -f /path/to/husker-schedules/logs/schedule_fetcher_$(date +%Y%m%d).log

# View cron output:
tail -f /path/to/husker-schedules/logs/cron.log
```

## Troubleshooting

### Cron Job Not Running

1. **Check cron service is running:**
   ```bash
   sudo systemctl status cron
   sudo systemctl start cron  # if not running
   ```

2. **Verify crontab syntax:**
   ```bash
   crontab -l  # Should show your jobs
   ```

3. **Check system logs:**
   ```bash
   grep CRON /var/log/syslog | tail -20
   ```

4. **Test the command manually:**
   ```bash
   cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py
   ```

### Permission Errors

```bash
# Ensure script is executable:
chmod +x scripts/schedule_fetcher.py

# Ensure directories are writable:
chmod 755 output/ logs/ tmp/
```

### Path Errors

If you get "command not found" errors, use full absolute paths:

```bash
# Find Python path:
which python3

# Find project path:
cd /path/to/husker-schedules && pwd
```

### Email Notifications

By default, cron sends email for any output. To disable:

```cron
MAILTO=""
0 6 * * * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

To enable email notifications:

```cron
MAILTO=your-email@example.com
0 6 * * * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py
```

## Example: Production Setup

Here's a recommended production cron configuration:

```cron
# Environment
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=""

# Nebraska Huskers Schedule Fetcher
# Runs every day at 6:00 AM and 6:00 PM
0 6,18 * * * cd /home/user/husker-schedules && /home/user/husker-schedules/venv/bin/python3 /home/user/husker-schedules/scripts/schedule_fetcher.py >> /home/user/husker-schedules/logs/cron.log 2>&1

# Weekly log cleanup - Every Sunday at 2 AM
0 2 * * 0 find /home/user/husker-schedules/logs -name "*.log" -mtime +30 -delete
```

## Testing Cron Schedule

To test if your cron schedule is correct, you can use online tools:

- https://crontab.guru/
- https://crontab-generator.org/

Simply paste your cron expression (the first 5 fields) to see when it will run.

## Quick Reference

| Schedule | Cron Expression | Description |
|----------|----------------|-------------|
| Every minute | `* * * * *` | For testing only |
| Every hour | `0 * * * *` | Every hour at minute 0 |
| Every 6 hours | `0 */6 * * *` | At 0:00, 6:00, 12:00, 18:00 |
| Daily at 6 AM | `0 6 * * *` | Recommended |
| Twice daily | `0 6,18 * * *` | 6 AM and 6 PM |
| Weekly on Monday | `0 8 * * 1` | Monday at 8 AM |
| Monthly on 1st | `0 0 1 * *` | First day at midnight |

## Recommended Schedule for Sports Schedules

For sports schedule updates, we recommend:

**During active seasons:**
```cron
0 6,18 * * * cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

**Off-season:**
```cron
0 7 * * 1 cd /path/to/husker-schedules && venv/bin/python3 scripts/schedule_fetcher.py >> logs/cron.log 2>&1
```

This provides frequent updates during games while conserving API usage during off-season.
