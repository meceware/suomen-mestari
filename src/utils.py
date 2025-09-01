"""
Utility functions for the text-to-speech Finnish learning project.
"""

import os
import re
import logging
from typing import List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/output.log'),
            logging.StreamHandler()
        ]
    )
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

def create_safe_filename(text: str, max_length: int = 50) -> str:
    """
    Create a safe filename from text content.
    """
    # Remove special characters and replace spaces with underscores
    safe_text = re.sub(r'[^\w\s-]', '', text)
    safe_text = re.sub(r'[-\s]+', '-', safe_text)

    # Truncate if too long
    if len(safe_text) > max_length:
        safe_text = safe_text[:max_length]

    return safe_text.lower()

def get_config(key: str, default=None):
    """Get configuration value from environment variables."""
    return os.getenv(key, default)

def ensure_output_dir():
    """Ensure output directory exists."""
    output_dir = get_config('OUTPUT_DIR', './output')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def ensure_ai_processed_dir():
    """Ensure ai processed json directory exists."""
    ai_processed_dir = './ai_processed'
    os.makedirs(ai_processed_dir, exist_ok=True)
    return ai_processed_dir