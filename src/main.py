"""
Main application for Finnish text-to-speech learning system.
Processes markdown files and generates audio files for language learning.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import List
import json

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import setup_logging, ensure_output_dir, ensure_ai_processed_dir
from mistune_parser import MistuneMarkdownParser, ContentSection
from translator import OllamaTranslator
from tts_generator import TTSGenerator

class LanguageTTSProcessor:
    """Main processor for language text-to-speech learning system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.parser = MistuneMarkdownParser()
        self.translator = OllamaTranslator()
        self.tts_generator = TTSGenerator()

        # Ensure output directory exists
        self.output_dir = ensure_output_dir()
        self.ai_processed_dir = ensure_ai_processed_dir()

        self.logger.info("Language TTS Processor initialized")

    def process_markdown_file(self, filepath: str) -> bool:
        """
        Process a markdown file and generate audio files.

        Args:
            filepath: Path to the markdown file to process

        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Validate file exists
            if not os.path.exists(filepath):
                self.logger.error(f"File not found: {filepath}")
                return False

            self.logger.info(f"Processing markdown file: {filepath}")

            # Parse the markdown file
            sections = self.parser.parse_file(filepath)
            if not sections:
                self.logger.warning(f"No content sections found in {filepath}")
                return False

            self.logger.info(f"Found {len(sections)} content sections")

            # Process each section
            success_count = 0
            base_filename = Path(filepath).stem

            for i, section in enumerate(sections):
                self.logger.info(f"Processing section {i+1}/{len(sections)}: {section.title}")

                if self._process_section(section, base_filename):
                    success_count += 1
                else:
                    self.logger.warning(f"Failed to process section: {section.title}")

            self.logger.info(f"Successfully processed {success_count}/{len(sections)} sections")
            return success_count > 0

        except Exception as e:
            self.logger.error(f"Error processing markdown file {filepath}: {e}")
            return False

    def _process_section(self, section: ContentSection, base_filename: str) -> bool:
        """
        Process a single content section using AI-powered translation.

        Args:
            section: ContentSection to process
            base_filename: Base filename for output files

        Returns:
            True if processing was successful, False otherwise
        """
        try:
            if not section.raw_content:
                self.logger.warning(f"No content in section: {section.title}")
                return False

            self.logger.info(f"Processing raw content ({len(section.raw_content)} characters)")

            # Create output filename
            filename = self.parser.create_filename(section, base_filename)
            ai_processed_path = os.path.join(self.ai_processed_dir, f'{filename}.json')

            ai_result = None
            if os.path.exists(ai_processed_path):
                try:
                    with open(ai_processed_path, 'r', encoding='utf-8') as f:
                        ai_result = json.load(f)
                        if ai_result and ai_result.get('sentences'):
                            self.logger.info(f"Skipping already processed section: {section.title}")
                except (json.JSONDecodeError, IOError) as e:
                    self.logger.debug(f"Could not load existing AI data for section '{section.title}': {e}")
                    ai_result = None

            if not ai_result or not ai_result.get('sentences'):
                # Use AI to process raw content and extract Finnish-English pairs
                ai_result = self.translator.process_content_with_ai(section.raw_content)
                if not ai_result or not ai_result.get('sentences'):
                    self.logger.warning(f"No Finnish-English pairs found in section: {section.title}")
                    return False

                with open(ai_processed_path, 'w', encoding='utf-8') as f:
                    json.dump(ai_result, f, ensure_ascii=False, indent=2)

            sentences = ai_result['sentences']
            self.logger.info(f"AI extracted {len(sentences)} Finnish-English pairs")

            # Generate audio for each Finnish → English pair with pauses
            self.logger.info("Generating learning audio (Finnish → pause → English for each sentence)...")
            audio = self.tts_generator.create_sentence_pair_audio(sentences)
            if not audio:
                self.logger.error(f"Audio generation failed for section: {section.title}")
                return False

            # Save audio file
            output_path = os.path.join(self.output_dir, f'{filename}.mp3')
            if self.tts_generator.save_audio(audio, output_path):
                self.logger.info(f"Successfully created: {filename}.mp3")
                return True
            else:
                self.logger.error(f"Failed to save audio: {filename}.mp3")
                return False

        except Exception as e:
            self.logger.error(f"Error processing section {section.title}: {e}")
            return False

    def check_system_requirements(self) -> bool:
        """
        Check if all system requirements are met.

        Returns:
            True if all requirements are met, False otherwise
        """
        self.logger.info("Checking system requirements...")

        requirements_met = True

        # Check Ollama connection
        if not self.translator.is_available():
            self.logger.error("Ollama translator is not available")
            requirements_met = False
        else:
            self.logger.info("✓ Ollama translator is available")

        # Check Piper TTS
        if not self.tts_generator.is_available():
            self.logger.error("Piper TTS is not available")
            requirements_met = False
        else:
            self.logger.info("✓ Piper TTS is available")

        # Check output directory
        if not os.path.exists(self.output_dir):
            self.logger.error(f"Output directory not accessible: {self.output_dir}")
            requirements_met = False
        else:
            self.logger.info(f"✓ Output directory ready: {self.output_dir}")

        return requirements_met

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Finnish Text-to-Speech Learning System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py kappale-6.md
  python main.py ../suomen-mestari-1/kappale-6.md

This will process the markdown file and generate MP3 audio files
in the output directory with Finnish speech followed by English translations.
        """
    )

    parser.add_argument(
        'markdown_file',
        nargs='?',
        help='Path to the markdown file to process'
    )

    parser.add_argument(
        '--check-requirements',
        action='store_true',
        help='Check system requirements and exit'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)
    logger.info("Starting Language TTS Learning System")

    try:
        # Initialize processor
        processor = LanguageTTSProcessor()

        # Check requirements if requested
        if args.check_requirements:
            if processor.check_system_requirements():
                logger.info("All system requirements are met!")
                sys.exit(0)
            else:
                logger.error("System requirements not met. Please check the errors above.")
                sys.exit(1)

        # Validate markdown file is provided
        if not args.markdown_file:
            logger.error("Markdown file is required. Use --help for usage information.")
            sys.exit(1)

        # Check requirements before processing
        if not processor.check_system_requirements():
            logger.error("System requirements not met. Use --check-requirements for details.")
            sys.exit(1)

        # Process the markdown file
        success = processor.process_markdown_file(args.markdown_file)

        if success:
            logger.info("Processing completed successfully!")
            logger.info(f"Audio files saved to: {processor.output_dir}")
            sys.exit(0)
        else:
            logger.error("Processing failed. Check the logs for details.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
