#!/usr/bin/env python3
"""
Nebraska Huskers Schedule Fetcher
Fetches sports schedules using Claude AI API and manages the output files.
"""

import os
import json
import logging
import zipfile
import shutil
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import anthropic
from dotenv import load_dotenv

# Setup logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            LOG_DIR /
            f"schedule_fetcher_{datetime.now().strftime('%Y%m%d')}.log"
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScheduleFetcher:
    """Handles fetching and processing Nebraska sports schedules via
    Claude API."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the schedule fetcher with configuration."""
        # Load environment variables
        load_dotenv(Path(__file__).parent.parent / "config" / ".env")

        # Load configuration
        self.config = self._load_config(config_path)

        # Load sports configuration
        self.sports = self._load_sports_config()

        # Initialize Anthropic client
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment variables"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)

        # Setup directories
        self.base_dir = Path(__file__).parent.parent
        self.tmp_dir = self.base_dir / "tmp"

        # Get output directory from environment variable or use default
        output_dir_env = os.getenv("OUTPUT_DIRECTORY")
        if output_dir_env:
            self.output_dir = Path(output_dir_env)
            logger.info(
                f"Using OUTPUT_DIRECTORY from environment: {self.output_dir}"
            )
        else:
            self.output_dir = self.base_dir / self.config.get(
                "output_directory", "output"
            )
            logger.info(
                f"Using default output directory: {self.output_dir}"
            )

        self.sport_prompt_template_file = (
            self.base_dir / "prompt-sport-template.txt"
        )
        self.html_prompt_file = (
            self.base_dir / "prompt-html-generator.txt"
        )

        # Ensure directories exist
        if not self.tmp_dir.exists():
            self.tmp_dir.mkdir(parents=True)

        # Handle output directory creation carefully
        # (especially for symlinks and Google Drive paths)
        if self.output_dir.is_symlink():
            # If it's a symlink, check if the target exists
            target = self.output_dir.resolve()
            if not target.exists():
                # Create the target directory
                target.mkdir(parents=True)
        elif not self.output_dir.exists():
            # Not a symlink and doesn't exist - create it
            self.output_dir.mkdir(parents=True)
        elif not self.output_dir.is_dir():
            raise ValueError(
                f"Output path exists but is not a directory: "
                f"{self.output_dir}"
            )

        logger.info("ScheduleFetcher initialized successfully")

    def _load_config(
            self, config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent / "config" / "config.json"
            )
        else:
            config_path = Path(config_path)

        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            logger.warning(
                f"Config file not found at {config_path}, using defaults"
            )
            return {
                "model": "claude-sonnet-4-5-20250929",
                "max_tokens": 64000,
                "temperature": 1.0,
                "thinking_budget": 5000,
                "delay_between_sports": 30,
                "output_directory": "output"
            }

    def _load_sports_config(self) -> List[Dict[str, str]]:
        """Load sports configuration from JSON file."""
        sports_config_path = (
            Path(__file__).parent.parent / "config" / "sports.json"
        )

        if sports_config_path.exists():
            with open(sports_config_path, 'r') as f:
                config = json.load(f)
                return config.get("sports", [])
        else:
            logger.warning(
                f"Sports config file not found at {sports_config_path}, "
                f"using defaults"
            )
            return [
                {"name": "Football", "filename": "Football.csv"},
                {"name": "Baseball", "filename": "Baseball.csv"},
                {"name": "Softball", "filename": "Softball.csv"},
                {
                    "name": "Men's Basketball",
                    "filename": "MensBasketball.csv"
                },
                {
                    "name": "Women's Basketball",
                    "filename": "WomensBasketball.csv"
                },
                {"name": "Volleyball", "filename": "Volleyball.csv"}
            ]

    def _read_prompt_template(
            self, template_file: Path,
            replacements: Dict[str, str] = None
    ) -> str:
        """Read a prompt template file and replace placeholders."""
        if not template_file.exists():
            raise FileNotFoundError(
                f"Prompt template file not found: {template_file}"
            )

        with open(template_file, 'r') as f:
            prompt = f.read()

        # Replace placeholders if provided
        if replacements:
            for key, value in replacements.items():
                placeholder = f"{{{{{key}}}}}"  # {{KEY}}
                prompt = prompt.replace(placeholder, value)

        logger.info(
            f"Loaded prompt template from {template_file}"
        )
        return prompt

    def _call_claude_api(self, prompt: str) -> Dict[str, Any]:
        """Call the Claude API with the given prompt and handle tool
        use loop."""
        logger.info(
            "Calling Claude API with extended thinking and web search..."
        )

        try:
            messages = [{"role": "user", "content": prompt}]

            # Tool use loop
            max_iterations = 25
            for iteration in range(max_iterations):
                logger.info(
                    f"API iteration {iteration + 1}/{max_iterations}..."
                )

                # Add delay between iterations to avoid rate limits
                # (except first call)
                if iteration > 0:
                    delay = 3  # 3 second delay between iterations
                    logger.info(
                        f"Waiting {delay} seconds before next API call..."
                    )
                    time.sleep(delay)

                # Retry logic for rate limits
                max_retries = 5
                for retry in range(max_retries):
                    try:
                        # Use streaming for large responses
                        with self.client.messages.stream(
                            model=self.config.get(
                                "model", "claude-sonnet-4-5-20250929"
                            ),
                            max_tokens=self.config.get("max_tokens", 64000),
                            temperature=self.config.get("temperature", 1.0),
                            thinking={
                                "type": "enabled",
                                "budget_tokens": self.config.get(
                                    "thinking_budget", 5000
                                )
                            },
                            tools=[{
                                "type": "web_search_20250305",
                                "name": "web_search",
                                "max_uses": 10
                            }],
                            messages=messages
                        ) as stream:
                            response = stream.get_final_message()
                        break  # Success, exit retry loop

                    except anthropic.RateLimitError:
                        if retry < max_retries - 1:
                            # Exponential backoff: 60s, 120s, 240s, 480s
                            wait_time = 60 * (2 ** retry)
                            logger.warning(
                                f"Rate limit hit. Waiting {wait_time} seconds "
                                f"before retry {retry + 1}/{max_retries}..."
                            )
                            time.sleep(wait_time)
                        else:
                            logger.error("Max retries exceeded for rate limit")
                            raise

                logger.info(
                    f"Response ID: {response.id}, "
                    f"Stop reason: {response.stop_reason}"
                )

                # If we got a final answer, return it
                if (response.stop_reason == "end_turn" or
                        response.stop_reason == "max_tokens"):
                    logger.info("Received final response")
                    return response

                # If Claude wants to use a tool
                if response.stop_reason == "tool_use":
                    # Add assistant's response to conversation
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Extract tool uses and create a simple continuation
                    # The web search is executed server-side, we just continue
                    tool_use_count = sum(
                        1 for block in response.content
                        if hasattr(block, 'type') and block.type == 'tool_use'
                    )
                    logger.info(
                        f"Found {tool_use_count} tool use(s), "
                        f"continuing conversation..."
                    )

                    # Continue with a simple prompt to get the final answer
                    messages.append({
                        "role": "user",
                        "content": "Please provide the complete schedules "
                                   "based on your search results."
                    })
                    continue

                # Some other stop reason
                logger.warning(
                    f"Unexpected stop reason: {response.stop_reason}"
                )
                return response

            logger.error(f"Exceeded maximum iterations ({max_iterations})")
            return response

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            raise

    def _extract_code_blocks(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract code blocks with filenames from Claude's response.
        Returns list of (filename, content) tuples.
        """
        # Pattern to match code blocks with filenames: ```type:filename
        pattern = r'```(?:csv|html):([^\n]+)\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)

        files = []
        for filename, content in matches:
            filename = filename.strip()
            content = content.strip()
            files.append((filename, content))
            logger.info(f"Extracted code block for file: {filename}")

        return files

    def _download_artifact(self, message: Any) -> int:
        """Extract and save files from code blocks in the API response."""
        logger.info("Processing API response for code blocks...")

        files_saved = 0

        # Collect all text blocks from the response
        all_text = []
        for block in message.content:
            if hasattr(block, 'type'):
                if block.type == 'text':
                    all_text.append(block.text)
                    logger.info(f"Found text block ({len(block.text)} chars)")

        if not all_text:
            logger.warning("No text blocks found in response")
            return 0

        # Combine all text blocks
        combined_text = '\n\n'.join(all_text)
        logger.info(f"Combined text length: {len(combined_text)} chars")

        # Save the full response to a temporary file for inspection
        response_file = (
            self.tmp_dir /
            f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        with open(response_file, 'w') as f:
            f.write(combined_text)
        logger.info(
            f"Saved full response to {response_file}"
        )

        # Extract code blocks with filenames from combined text
        files = self._extract_code_blocks(combined_text)

        if not files:
            logger.warning(
                "No code blocks with filenames found in response"
            )
            return 0

        # Save each file to the output directory
        for filename, content in files:
            output_path = self.output_dir / filename
            with open(output_path, 'w') as f:
                f.write(content)
            logger.info(
                f"Saved {filename} to {self.output_dir}"
            )
            files_saved += 1

        if files_saved == 0:
            logger.warning("No files extracted from response")
        else:
            logger.info(
                f"Successfully extracted and saved {files_saved} files"
            )

        return files_saved

    def _extract_zip_from_response(
            self, response_file: Path
    ) -> Optional[Path]:
        """
        Extract zip file path or content from Claude's response.
        This method should be customized based on how Claude returns the
        artifact.
        """
        # If Claude provides a download link or base64 encoded zip,
        # handle it here. For now, we'll look for any zip files that might
        # have been created

        # Check if response mentions a zip file
        with open(response_file, 'r') as f:
            content = f.read()

        # Look for zip file references in the response
        if 'scheduled-sources.zip' in content or '.zip' in content:
            logger.info(
                "Response mentions zip file - checking for artifact"
            )
            # The actual implementation would depend on Claude's artifact
            # delivery method. This might involve downloading from a URL or
            # decoding base64 content

        return None

    def _extract_and_move_files(self, zip_path: Path):
        """Extract zip file and move contents to output directory."""
        logger.info(f"Extracting {zip_path}...")

        try:
            # Create temporary extraction directory
            extract_dir = (
                self.tmp_dir /
                f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            extract_dir.mkdir(exist_ok=True)

            # Extract zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            logger.info(f"Extracted files to {extract_dir}")

            # Move files to output directory
            # Look for schedule-sources folder
            schedule_sources = extract_dir / "schedule-sources"
            if schedule_sources.exists():
                # Move all files from schedule-sources to output
                for file_path in schedule_sources.iterdir():
                    if file_path.is_file():
                        dest_path = self.output_dir / file_path.name
                        shutil.copy2(file_path, dest_path)
                        logger.info(
                            f"Moved {file_path.name} to {self.output_dir}"
                        )
            else:
                # If no schedule-sources folder, move all files
                for file_path in extract_dir.rglob('*'):
                    if file_path.is_file():
                        dest_path = self.output_dir / file_path.name
                        shutil.copy2(file_path, dest_path)
                        logger.info(
                            f"Moved {file_path.name} to {self.output_dir}"
                        )

            # Clean up temporary extraction directory
            shutil.rmtree(extract_dir)
            logger.info("Cleanup completed")

        except Exception as e:
            logger.error(f"Error extracting and moving files: {e}")
            raise

    def _cleanup_tmp(self):
        """Clean up temporary files older than 24 hours."""
        logger.info("Cleaning up temporary files...")

        # 24 hours ago
        cutoff_time = datetime.now().timestamp() - (24 * 60 * 60)

        for item in self.tmp_dir.iterdir():
            if item.is_file() and item.stat().st_mtime < cutoff_time:
                item.unlink()
                logger.info(
                    f"Removed old temp file: {item.name}"
                )
            elif item.is_dir() and item.stat().st_mtime < cutoff_time:
                shutil.rmtree(item)
                logger.info(
                    f"Removed old temp directory: {item.name}"
                )

    def _verify_filesystem_permissions(self):
        """Verify that all required directories exist and are writable."""
        logger.info("Verifying filesystem permissions...")

        directories_to_check = [
            ("output", self.output_dir),
            ("tmp", self.tmp_dir),
            ("logs", LOG_DIR)
        ]

        for name, directory in directories_to_check:
            # Check if directory exists
            if not directory.exists():
                error_msg = (
                    f"{name} directory does not exist: {directory}"
                )
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            # Check if directory is writable
            if not os.access(directory, os.W_OK):
                error_msg = (
                    f"{name} directory is not writable: {directory}"
                )
                logger.error(error_msg)
                raise PermissionError(error_msg)

            logger.info(
                f"{name} directory is writable: {directory}"
            )

        # Try to create a test file in output directory
        test_file = self.output_dir / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            logger.info("Filesystem write test successful")
        except Exception as e:
            error_msg = (
                f"Failed to write test file to output directory: {e}"
            )
            logger.error(error_msg)
            raise PermissionError(error_msg)

    def _fetch_sport_schedule(
            self, sport_name: str, filename: str
    ) -> bool:
        """Fetch schedule for a single sport."""
        logger.info(f"Fetching schedule for {sport_name}...")

        try:
            # Read and prepare sport-specific prompt
            replacements = {
                "SPORT_NAME": sport_name,
                "FILENAME": filename
            }
            prompt = self._read_prompt_template(
                self.sport_prompt_template_file, replacements
            )

            # Call Claude API
            response = self._call_claude_api(prompt)

            # Extract files from code blocks in response
            files_saved = self._download_artifact(response)

            if files_saved > 0:
                logger.info(
                    f"Successfully saved schedule for {sport_name}"
                )
                return True
            else:
                logger.warning(
                    f"No schedule file extracted for {sport_name}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error fetching schedule for {sport_name}: {e}",
                exc_info=True
            )
            return False

    def _generate_html_page(self) -> bool:
        """Generate HTML page from existing CSV files using Python."""
        logger.info(
            "Generating HTML page from CSV files using Python generator..."
        )

        try:
            # Import the HTML generator
            from html_generator import generate_schedule_html

            # Check which CSV files exist
            available_sports = []
            for sport in self.sports:
                csv_path = self.output_dir / sport["filename"]
                if csv_path.exists():
                    available_sports.append(sport)
                else:
                    logger.warning(
                        f"CSV file not found for {sport['name']}: "
                        f"{sport['filename']}"
                    )

            if not available_sports:
                logger.error(
                    "No CSV files found to generate HTML page"
                )
                return False

            logger.info(
                f"Generating HTML from {len(available_sports)} sport(s)..."
            )

            # Generate HTML using Python (no API call!)
            output_path = generate_schedule_html(
                self.output_dir, self.sports
            )

            logger.info(
                f"Successfully generated HTML page at: {output_path}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error generating HTML page: {e}", exc_info=True
            )
            return False

    def run(self):
        """Main execution method."""
        logger.info("=" * 50)
        logger.info("Starting schedule fetch process")
        logger.info("=" * 50)

        try:
            # Verify filesystem permissions before making expensive API call
            self._verify_filesystem_permissions()

            # Process each sport separately
            successful_sports = 0
            delay_between_sports = self.config.get("delay_between_sports", 30)

            for index, sport in enumerate(self.sports):
                logger.info(
                    f"Processing {sport['name']} "
                    f"({index + 1}/{len(self.sports)})..."
                )
                if self._fetch_sport_schedule(
                        sport["name"], sport["filename"]):
                    successful_sports += 1

                # Add delay between sports to avoid rate limits
                # (except after last sport)
                if index < len(self.sports) - 1:
                    logger.info(
                        f"Waiting {delay_between_sports} seconds before "
                        f"next sport to avoid rate limits..."
                    )
                    time.sleep(delay_between_sports)

            logger.info(
                f"Successfully fetched {successful_sports}/"
                f"{len(self.sports)} sports schedules"
            )

            # Generate HTML page from the CSV files
            if successful_sports > 0:
                logger.info(
                    f"Waiting {delay_between_sports} seconds before "
                    f"generating HTML page..."
                )
                time.sleep(delay_between_sports)

                logger.info("Generating HTML page...")
                if self._generate_html_page():
                    logger.info("HTML page generated successfully")
                else:
                    logger.warning("Failed to generate HTML page")

            # Cleanup old temporary files
            self._cleanup_tmp()

            logger.info("=" * 50)
            logger.info("Schedule fetch process completed")
            logger.info(
                f"Total sports processed: {successful_sports}/"
                f"{len(self.sports)}"
            )
            logger.info("=" * 50)
            return successful_sports > 0

        except Exception as e:
            logger.error(
                f"Error in schedule fetch process: {e}", exc_info=True
            )
            return False


def main():
    """Main entry point for the script."""
    try:
        fetcher = ScheduleFetcher()
        success = fetcher.run()
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
