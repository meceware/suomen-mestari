# Finnish Text-to-Speech Learning System

A Python-based system that converts Finnish learning materials (markdown files from Suomen Mestari) into audio files for language learning. The system extracts Finnish text, translates it to English using AI (Ollama), and generates audio files with Finnish speech followed by English translations.

I am not a native Finnish speaker, so please report any issues with translations or pronunciations. I will try to fix them as they are reported.

## Why?

I am a busy person who wants to learn Finnish. I find it easier to learn when I can listen to the material while doing other things, like commuting or exercising. This system allows me to create audio files from my existing learning materials.

## Features

- **Markdown Processing**: Extracts Finnish content from structured markdown files
- **AI Translation**: Uses Ollama (gemma3:12b) for Finnish-to-English translation
- **High-Quality TTS**: Uses Piper TTS or Edge TTS for natural-sounding speech synthesis
- **Learning Format**: Generates audio with Finnish → pause → English pattern
- **Organized Output**: Creates descriptively named MP3 files by content section

## System Requirements

- Python 3.9 or higher
- Ollama server running with gemma3:12b model or any other capable model

## Installation

### 1. Clone and Setup Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux/Mac:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy and edit the `.env` file to match your setup:

```bash
# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:12b

# TTS Engine Selection
TTS_ENGINE=edge  # Options: piper, edge

# Piper TTS Voice Configuration
PIPER_VOICE_FI=fi_FI-asmo-medium
PIPER_VOICE_EN=en_US-lessac-high

# Edge TTS Voice Configuration (Microsoft voices)
EDGE_VOICE_FI=fi-FI-HarriNeural  # Options: fi-FI-HarriNeural, fi-FI-NooraNeural
EDGE_VOICE_EN=en-US-JennyNeural  # Options: en-US-JennyNeural, en-US-GuyNeural, en-US-AriaNeural

# Audio Configuration
OUTPUT_DIR=./output
PAUSE_DURATION=2.0
AUDIO_FORMAT=mp3
SAMPLE_RATE=22050
```

### 3. Verify Installation

```bash
# Check system requirements
python3 src/main.py --check-requirements
```

## Usage

### Basic Usage

```bash
# Process a markdown file
python3 src/main.py suomen-mestari-1/kappale-6.md

# With verbose logging
python3 src/main.py -v suomen-mestari-1/kappale-6.md
```

### Command Line Options

```bash
python3 src/main.py [OPTIONS] MARKDOWN_FILE

Options:
  --check-requirements    Check system requirements and exit
  --verbose, -v          Enable verbose logging
  --help                 Show help message
```

## Output

The system generates MP3 files in the `output/` directory with descriptive names:

## Configuration

### Voice Options

The system supports multiple voice models on Piper. Edit `.env` to change voices:

```bash
# Finnish voices (alternatives)
PIPER_VOICE_FI=fi_FI-harri-low      # Lower quality, faster
PIPER_VOICE_FI=fi_FI-harri-medium   # Balanced (default)

# English voices (alternatives)
PIPER_VOICE_EN=en_US-lessac-low     # Female voice, lower quality
PIPER_VOICE_EN=en_US-lessac-medium  # Female voice, medium quality
PIPER_VOICE_EN=en_US-lessac-high    # Female voice, higher quality (default)
PIPER_VOICE_EN=en_US-amy-medium     # Alternative female voice
```

The system support multiple voice modes on Edge TTS. Edit `.env` to change voices:

```bash
# Finnish voices (alternatives)
EDGE_VOICE_FI=fi-FI-HarriNeural  # Options: fi-FI-HarriNeural, fi-FI-NooraNeural, fi-FI-SelmaNeural

# English voices (alternatives)
EDGE_VOICE_EN=en-US-JennyNeural  # Options: see `edge-tts --list-voices` for options
```

### Audio Settings

```bash
PAUSE_DURATION=2.0      # Pause between Finnish and English (seconds)
SAMPLE_RATE=22050       # Audio quality (Hz)
AUDIO_FORMAT=mp3        # Output format
```

## License

This project is open source. Please check individual dependencies for their licenses.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the logs for error details
3. Ensure all system requirements are met
4. Verify configuration in `.env` file
