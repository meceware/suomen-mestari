# Text-to-Speech Learning System

A customizable Python-based Text-to-Speech (TTS) system designed for language learning. Convert YAML translation files into audio with proper timing between languages, supporting multiple TTS engines with automatic fallback. Works with any language pair supported by the TTS engines.

## Why?

I am a busy person who wants to learn Finnish. I find it easier to learn when I can listen to the material while doing other things, like commuting or exercising. This system allows me to create audio files from my existing learning materials.

I am not a native Finnish speaker, so please report any issues with translations or pronunciations. I will try to fix them as they are reported.

## Features

- **Multiple TTS Engines**: Support for Edge-TTS, Google TTS (gTTS), Piper TTS, and Coqui TTS
- **Automatic Fallback**: If one engine fails, automatically tries alternative engines
- **Customizable Timing**: Configure delays between languages and translation pairs
- **Batch Processing**: Process multiple translations in a single file
- **Audio Combining**: Automatically combines all translations into a single MP3 file
- **Language Agnostic**: Works with any languages supported by the TTS engines
- **Interactive Mode**: User-friendly interactive mode for easy processing

## Installation

### Prerequisites

- Python 3.9 or higher
- FFmpeg (required for audio processing)

### Install FFmpeg

FFmpeg is required by the `pydub` library for audio processing operations.

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg libavcodec-extra
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [FFmpeg official website](https://ffmpeg.org/download.html). Add `ffmpeg` binaries to your `PATH`.

### Setup

```bash
# Clone the repository
git clone https://github.com/meceware/suomen-mestari.git .

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

### Configure

Check `config/config.yaml` for default configuration. Change as necessary.

## Usage

### Basic Usage

```bash
# Interactive mode
python src/main.py interactive

# Process a translation file
python src/main.py translate data/suomen-mestari-1/kappale-6/01-kappale-6.yaml

# Process directory of translation files
python src/main.py translate data/suomen-mestari-1/kappale-6
```

### Command Line Options

```bash
$ python src/main.py --help
Usage: main.py [OPTIONS] COMMAND [ARGS]...

  Text-to-Speech Learning System - Convert translations to audio

Options:
  --verbose  Enable verbose logging
  --help     Show this message and exit.

Commands:
  create-sample  Create a sample translation file
  interactive    Interactive mode for processing translations
  list-engines   List available TTS engines
  test-engine    Test a specific TTS engine
  test-voices    Test all available voices for a given language and text
  translate      Process a translation file or directory of translation...
```

## Output

The system generates MP3 files in the `output/` directory with descriptive names.

## TTS Engines

### Edge-TTS (Recommended)
- **Pros**: High quality, free, no API key required
- **Cons**: Requires internet connection
- **Languages**: Excellent support for 50+ languages including major European, Asian, and Middle Eastern languages

### Google TTS (gTTS)
- **Pros**: Simple, reliable, free
- **Cons**: Limited voice options, requires internet
- **Languages**: Good support for many languages

### Piper TTS
- **Pros**: Offline capability, privacy-focused
- **Cons**: Requires model downloads, limited voices
- **Installation**: May require additional setup for models

### Coqui TTS
- **Pros**: High quality, advanced features, offline capable
- **Cons**: Resource intensive, large model files
- **Note**: First run will download required models

## License

This project is licensed under the MIT. Please check individual dependencies for their licenses.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on the repository.
