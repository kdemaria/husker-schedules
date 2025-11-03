#!/usr/bin/env python3
"""
Test script for HTML generation
Generates HTML from existing CSV files without calling Claude API
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from html_generator import generate_schedule_html  # noqa: E402


def main():
    """Test the HTML generator with existing CSV files."""
    # Setup paths
    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "output"
    sports_config_path = base_dir / "config" / "sports.json"

    # Create output directory if it doesn't exist
    # Handle case where output_dir is a symlink
    if output_dir.is_symlink():
        # If it's a symlink, check if the target exists
        target = output_dir.resolve()
        if not target.exists():
            # Create the target directory
            target.mkdir(parents=True)
    elif not output_dir.exists():
        # Not a symlink and doesn't exist - create it
        output_dir.mkdir(parents=True)
    elif not output_dir.is_dir():
        print(
            f"✗ Error: Output path exists but is not a directory: "
            f"{output_dir}"
        )
        return 1

    # Load sports configuration
    if sports_config_path.exists():
        with open(sports_config_path, 'r') as f:
            config = json.load(f)
            sports_config = config.get('sports', [])
    else:
        # Default sports configuration
        sports_config = [
            {"name": "Football", "filename": "Football.csv"},
            {"name": "Baseball", "filename": "Baseball.csv"},
            {"name": "Softball", "filename": "Softball.csv"},
            {"name": "Men's Basketball", "filename": "MensBasketball.csv"},
            {"name": "Women's Basketball", "filename": "WomensBasketball.csv"},
            {"name": "Volleyball", "filename": "Volleyball.csv"}
        ]

    print("=" * 60)
    print("Nebraska Huskers HTML Generator - Test Mode")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print(f"Sports to process: {len(sports_config)}")
    print()

    # Check which CSV files exist
    print("Checking for CSV files:")
    available_sports = []
    for sport in sports_config:
        csv_path = output_dir / sport['filename']
        exists = csv_path.exists()
        status = "✓ Found" if exists else "✗ Missing"
        print(f"  {status}: {sport['filename']}")
        if exists:
            available_sports.append(sport)

    print()

    if not available_sports:
        print("⚠️  No CSV files found. Cannot generate HTML.")
        print(
            "   Please run the schedule fetcher first or create sample "
            "CSV files."
        )
        return 1

    # Generate HTML
    print(f"Generating HTML from {len(available_sports)} sport(s)...")
    try:
        output_path = generate_schedule_html(output_dir, sports_config)
        print(f"✓ Success! HTML generated at: {output_path}")
        print()
        print("You can view it by opening the file in a browser:")
        print(f"  file://{output_path.absolute()}")
        return 0
    except Exception as e:
        print(f"✗ Error generating HTML: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
