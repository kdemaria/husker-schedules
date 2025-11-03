#!/usr/bin/env python3
"""
HTML Generator for Nebraska Huskers Schedules
Generates a consistent HTML page matching wacornhuskers.com design
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict


# Sport emojis
SPORT_EMOJIS = {
    "Football": "🏈",
    "Volleyball": "🏐",
    "Men's Basketball": "🏀",
    "Women's Basketball": "🏀",
    "Softball": "🥎",
    "Baseball": "⚾"
}


class HuskersHTMLGenerator:
    """Generates HTML schedule pages with Nebraska Huskers branding."""

    def __init__(self, output_dir: Path):
        """Initialize the HTML generator.

        Args:
            output_dir: Directory containing CSV files and where HTML
                        will be saved
        """
        self.output_dir = Path(output_dir)

    def read_csv(self, filename: str) -> List[Dict[str, str]]:
        """Read a CSV file and return rows as dictionaries.

        Args:
            filename: Name of the CSV file

        Returns:
            List of dictionaries representing each row
        """
        csv_path = self.output_dir / filename
        if not csv_path.exists():
            return []

        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows

    def format_game_row(self, game: Dict[str, str]) -> str:
        """Format a single game row as HTML.

        Args:
            game: Dictionary containing game data

        Returns:
            HTML string for the table row
        """
        # Determine if this is a past or future game
        result = game.get('Result', '').strip()
        row_class = 'game-completed' if result else 'game-upcoming'

        # Determine location class for border color
        location = game.get('Location', '').strip()
        if location.lower() in ['home', 'lincoln ne']:
            location_class = 'home-game'
        elif ('neutral' in location.lower() or
              any(city in location.lower()
                  for city in ['kansas city', 'sioux falls'])):
            location_class = 'neutral-game'
        else:
            location_class = 'away-game'

        # Build the row with both classes
        html = (
            f'                        '
            f'<tr class="{row_class} {location_class}">\n'
        )
        html += (
            f'                            <td>{game.get("Date", "")}</td>\n'
        )
        html += (
            f'                            <td>{game.get("Day", "")}</td>\n'
        )
        html += (
            f'                            '
            f'<td>{game.get("Opponent", "")}</td>\n'
        )
        html += f'                            <td>{location}</td>\n'
        html += (
            f'                            '
            f'<td>{game.get("Venue", "")}</td>\n'
        )
        html += (
            f'                            <td>{game.get("Time", "")}</td>\n'
        )

        # Event with badge styling if present
        event = game.get("Event", "").strip()
        if event:
            html += (
                f'                            '
                f'<td><span class="event-badge">{event}</span></td>\n'
            )
        else:
            html += '                            <td></td>\n'

        # Watch channel with badge styling if present
        watch = game.get("Watch", "").strip()
        if watch:
            html += (
                f'                            '
                f'<td><span class="watch-channel">{watch}</span></td>\n'
            )
        else:
            html += '                            <td></td>\n'

        # Result cell with special styling for wins/losses
        result_html = ''
        if result:
            if result.startswith('W'):
                result_html = f'<span class="result-win">{result}</span>'
            elif result.startswith('L'):
                result_html = f'<span class="result-loss">{result}</span>'
            else:
                result_html = result
        else:
            result_html = '<span class="result-upcoming">—</span>'

        html += f'                            <td>{result_html}</td>\n'
        html += '                        </tr>\n'

        return html

    def generate_sport_section(self, sport_name: str, filename: str) -> str:
        """Generate HTML section for a single sport.

        Args:
            sport_name: Display name of the sport
            filename: CSV filename for this sport

        Returns:
            HTML string for the sport section
        """
        games = self.read_csv(filename)
        emoji = SPORT_EMOJIS.get(sport_name, "")

        if not games:
            return f'''        <!-- {sport_name.upper()} -->
        <section class="sport-section">
            <div class="sport-header">
                <h2>{emoji} {sport_name}</h2>
            </div>
            <div class="note-section">
                <p><strong>Schedule not yet available</strong></p>
                <p>Check back later for updates</p>
            </div>
        </section>

'''

        # Build the table
        html = f'''        <!-- {sport_name.upper()} -->
        <section class="sport-section">
            <div class="sport-header">
                <h2>{emoji} {sport_name}</h2>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Day</th>
                            <th>Opponent</th>
                            <th>Location</th>
                            <th>Venue</th>
                            <th>Time</th>
                            <th>Event</th>
                            <th>Watch</th>
                            <th>Result</th>
                        </tr>
                    </thead>
                    <tbody>
'''

        # Add each game
        for game in games:
            html += self.format_game_row(game)

        html += '''                    </tbody>
                </table>
            </div>
        </section>

'''

        return html

    def generate_html(self, sports_config: List[Dict[str, str]]) -> str:
        """Generate complete HTML page.

        Args:
            sports_config: List of dicts with 'name' and 'filename' keys

        Returns:
            Complete HTML document as string
        """
        # Get current timestamp
        now = datetime.now()
        last_updated = now.strftime("%B %d, %Y")
        year = now.strftime("%Y")

        # Start building HTML
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nebraska Cornhuskers Sports Schedules | {year}-{int(year)+1}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                         Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}

        .header {{
            background: linear-gradient(135deg, #D00000 0%, #8B0000 100%);
            color: #FEFDFA;
            padding: 2rem 1rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .header p {{
            font-size: 1.1rem;
            opacity: 0.95;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem 1rem;
        }}

        .sport-section {{
            background: white;
            margin-bottom: 3rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .sport-header {{
            background-color: #D00000;
            color: #FEFDFA;
            padding: 1.5rem;
            border-bottom: 4px solid #8B0000;
        }}

        .sport-header h2 {{
            font-size: 1.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .table-container {{
            overflow-x: auto;
            padding: 1rem;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
        }}

        thead {{
            background-color: #FEFDFA;
            border-bottom: 2px solid #D00000;
        }}

        th {{
            padding: 1rem 0.75rem;
            text-align: left;
            font-weight: 700;
            color: #D00000;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }}

        td {{
            padding: 0.9rem 0.75rem;
            border-bottom: 1px solid #e0e0e0;
        }}

        tbody tr {{
            transition: background-color 0.2s;
        }}

        tbody tr:hover {{
            background-color: #f9f9f9;
        }}

        .game-completed {{
            background-color: #f8f8f8;
        }}

        .game-upcoming {{
            background-color: white;
            font-weight: 500;
        }}

        .result-win {{
            color: #28a745;
            font-weight: 700;
        }}

        .result-loss {{
            color: #dc3545;
            font-weight: 700;
        }}

        .result-upcoming {{
            color: #6c757d;
            font-style: italic;
        }}

        .home-game {{
            border-left: 4px solid #D00000;
        }}

        .away-game {{
            border-left: 4px solid #666;
        }}

        .neutral-game {{
            border-left: 4px solid #0066cc;
        }}

        .watch-channel {{
            background-color: #D00000;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: 600;
            display: inline-block;
        }}

        .event-badge {{
            background-color: #FEFDFA;
            color: #D00000;
            border: 1px solid #D00000;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
        }}

        .note-section {{
            padding: 1rem 1.5rem;
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            margin: 1rem;
            border-radius: 4px;
        }}

        .note-section p {{
            color: #856404;
            margin: 0.25rem 0;
        }}

        .footer {{
            text-align: center;
            padding: 2rem 1rem;
            color: #666;
            font-size: 0.9rem;
        }}

        .last-updated {{
            background-color: #D00000;
            color: #FEFDFA;
            padding: 0.5rem 1rem;
            text-align: center;
            font-size: 0.9rem;
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8rem;
            }}

            .sport-header h2 {{
                font-size: 1.4rem;
            }}

            table {{
                font-size: 0.85rem;
            }}

            th, td {{
                padding: 0.6rem 0.4rem;
            }}

            th {{
                font-size: 0.75rem;
            }}
        }}

        @media (max-width: 480px) {{
            .header h1 {{
                font-size: 1.5rem;
            }}

            .container {{
                padding: 1rem 0.5rem;
            }}

            .table-container {{
                padding: 0.5rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌽 Nebraska Cornhuskers</h1>
        <p>Complete Sports Schedules | {year}-{int(year)+1} Season</p>
    </div>

    <div class="last-updated">
        Last Updated: {last_updated}
    </div>

    <div class="container">
'''

        # Add each sport section
        for sport in sports_config:
            html += self.generate_sport_section(
                sport['name'], sport['filename']
            )

        # Add footer
        html += '''    </div>

    <div class="footer">
        <p><strong>Go Big Red!</strong></p>
        <p>For official updates, visit <strong>huskers.com</strong></p>
        <p>&copy; 2025 Nebraska Cornhuskers Athletics</p>
    </div>
</body>
</html>
'''

        return html

    def save_html(self, html: str, filename: str = "index.html") -> Path:
        """Save HTML content to a file.

        Args:
            html: HTML content to save
            filename: Output filename (default: index.html)

        Returns:
            Path to the saved file
        """
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return output_path


def generate_schedule_html(
        output_dir: Path, sports_config: List[Dict[str, str]]
) -> Path:
    """Convenience function to generate HTML schedule page.

    Args:
        output_dir: Directory containing CSV files
        sports_config: List of sports with 'name' and 'filename' keys

    Returns:
        Path to generated HTML file
    """
    generator = HuskersHTMLGenerator(output_dir)
    html = generator.generate_html(sports_config)
    return generator.save_html(html)
