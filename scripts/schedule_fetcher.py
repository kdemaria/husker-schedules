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
        logging.FileHandler(LOG_DIR / f"schedule_fetcher_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScheduleFetcher:
    """Handles fetching and processing Nebraska sports schedules via Claude API."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the schedule fetcher with configuration."""
        # Load environment variables
        load_dotenv(Path(__file__).parent.parent / "config" / ".env")

        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize Anthropic client
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = anthropic.Anthropic(api_key=self.api_key)

        # Setup directories
        self.base_dir = Path(__file__).parent.parent
        self.tmp_dir = self.base_dir / "tmp"
        self.output_dir = self.base_dir / "output"
        self.prompt_file = self.base_dir / "prompt-schedule-getter.txt"

        # Ensure directories exist
        self.tmp_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        logger.info("ScheduleFetcher initialized successfully")

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.json"
        else:
            config_path = Path(config_path)

        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return {
                "model": "claude-sonnet-4-5-20250929",
                "max_tokens": 16000,
                "temperature": 1.0
            }

    def _read_prompt(self) -> str:
        """Read the prompt from the prompt file."""
        if not self.prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {self.prompt_file}")

        with open(self.prompt_file, 'r') as f:
            prompt = f.read()

        logger.info(f"Loaded prompt from {self.prompt_file}")
        return prompt

    def _call_claude_api(self, prompt: str) -> Dict[str, Any]:
        """Call the Claude API with the given prompt and handle tool use loop."""
        logger.info("Calling Claude API with extended thinking and web search...")

        try:
            messages = [{"role": "user", "content": prompt}]

            # Tool use loop
            max_iterations = 25
            for iteration in range(max_iterations):
                logger.info(f"API iteration {iteration + 1}/{max_iterations}...")

                response = self.client.messages.create(
                    model=self.config.get("model", "claude-sonnet-4-5-20250929"),
                    max_tokens=self.config.get("max_tokens", 16000),
                    temperature=self.config.get("temperature", 1.0),
                    thinking={
                        "type": "enabled",
                        "budget_tokens": 10000
                    },
                    tools=[{
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": 10
                    }],
                    messages=messages
                )

                logger.info(f"Response ID: {response.id}, Stop reason: {response.stop_reason}")

                # If we got a final answer, return it
                if response.stop_reason == "end_turn" or response.stop_reason == "max_tokens":
                    logger.info("Received final response")
                    return response

                # If Claude wants to use a tool
                if response.stop_reason == "tool_use":
                    # Add assistant's response to conversation
                    messages.append({"role": "assistant", "content": response.content})

                    # Extract tool uses and create a simple continuation
                    # The web search is executed server-side, we just continue
                    tool_use_count = sum(1 for block in response.content if hasattr(block, 'type') and block.type == 'tool_use')
                    logger.info(f"Found {tool_use_count} tool use(s), continuing conversation...")

                    # Continue with a simple prompt to get the final answer
                    messages.append({
                        "role": "user",
                        "content": "Please provide the complete schedules based on your search results."
                    })
                    continue

                # Some other stop reason
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
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

        # Check for text blocks with code blocks
        for block in message.content:
            if hasattr(block, 'type'):
                if block.type == 'text':
                    text_content = block.text

                    # Save the full response to a temporary file for inspection
                    response_file = self.tmp_dir / f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(response_file, 'w') as f:
                        f.write(text_content)
                    logger.info(f"Saved response to {response_file}")

                    # Extract code blocks with filenames
                    files = self._extract_code_blocks(text_content)

                    if not files:
                        logger.warning("No code blocks with filenames found in response")
                        return 0

                    # Save each file to the output directory
                    for filename, content in files:
                        output_path = self.output_dir / filename
                        with open(output_path, 'w') as f:
                            f.write(content)
                        logger.info(f"Saved {filename} to {self.output_dir}")
                        files_saved += 1

        if files_saved == 0:
            logger.warning("No files extracted from response")
        else:
            logger.info(f"Successfully extracted and saved {files_saved} files")

        return files_saved

    def _extract_zip_from_response(self, response_file: Path) -> Optional[Path]:
        """
        Extract zip file path or content from Claude's response.
        This method should be customized based on how Claude returns the artifact.
        """
        # If Claude provides a download link or base64 encoded zip, handle it here
        # For now, we'll look for any zip files that might have been created

        # Check if response mentions a zip file
        with open(response_file, 'r') as f:
            content = f.read()

        # Look for zip file references in the response
        if 'scheduled-sources.zip' in content or '.zip' in content:
            logger.info("Response mentions zip file - checking for artifact")
            # The actual implementation would depend on Claude's artifact delivery method
            # This might involve downloading from a URL or decoding base64 content

        return None

    def _extract_and_move_files(self, zip_path: Path):
        """Extract zip file and move contents to output directory."""
        logger.info(f"Extracting {zip_path}...")

        try:
            # Create temporary extraction directory
            extract_dir = self.tmp_dir / f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
                        logger.info(f"Moved {file_path.name} to {self.output_dir}")
            else:
                # If no schedule-sources folder, move all files
                for file_path in extract_dir.rglob('*'):
                    if file_path.is_file():
                        dest_path = self.output_dir / file_path.name
                        shutil.copy2(file_path, dest_path)
                        logger.info(f"Moved {file_path.name} to {self.output_dir}")

            # Clean up temporary extraction directory
            shutil.rmtree(extract_dir)
            logger.info("Cleanup completed")

        except Exception as e:
            logger.error(f"Error extracting and moving files: {e}")
            raise

    def _cleanup_tmp(self):
        """Clean up temporary files older than 24 hours."""
        logger.info("Cleaning up temporary files...")

        cutoff_time = datetime.now().timestamp() - (24 * 60 * 60)  # 24 hours ago

        for item in self.tmp_dir.iterdir():
            if item.is_file() and item.stat().st_mtime < cutoff_time:
                item.unlink()
                logger.info(f"Removed old temp file: {item.name}")
            elif item.is_dir() and item.stat().st_mtime < cutoff_time:
                shutil.rmtree(item)
                logger.info(f"Removed old temp directory: {item.name}")

    def run(self):
        """Main execution method."""
        logger.info("=" * 50)
        logger.info("Starting schedule fetch process")
        logger.info("=" * 50)

        try:
            # Read prompt
            prompt = self._read_prompt()

            # Call Claude API
            response = self._call_claude_api(prompt)

            # Extract files from code blocks in response
            files_saved = self._download_artifact(response)

            if files_saved > 0:
                logger.info(f"Successfully saved {files_saved} schedule files to {self.output_dir}")
            else:
                logger.warning("No schedule files were extracted from the response")
                logger.warning("Check the response file in tmp/ directory for details")

            # Cleanup old temporary files
            self._cleanup_tmp()

            logger.info("=" * 50)
            logger.info("Schedule fetch process completed successfully")
            logger.info("=" * 50)
            return True

        except Exception as e:
            logger.error(f"Error in schedule fetch process: {e}", exc_info=True)
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
