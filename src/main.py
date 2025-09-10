"""Main CLI interface for the Text-to-Speech Learning System"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
import tempfile

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.logging import RichHandler
import yaml

from tts_engine import TTSEngineManager
from translation_parser import TranslationParser
from audio_processor import AudioProcessor

# Setup rich console
console = Console()

# Setup logging
def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(message)s",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True)
        ]
    )

logger = logging.getLogger(__name__)

class TTSProcessor:
    """Main processor for TTS operations"""

    def __init__(self, config_path: Path = Path("config/config.yaml")):
        self.config = self._load_config(config_path)
        self.engine_manager = TTSEngineManager(self.config)
        self.parser = TranslationParser()
        self.audio_processor = AudioProcessor(self.config.get("audio", {}))

    def _load_config(self, config_path: Path) -> dict:
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            # Return default config
            return {
                "general": {
                    "default_engine": "edge-tts",
                    "fallback_order": ["gtts", "piper", "coqui"],
                },
                "engines": {}
            }

    def _get_language_code(self, language_name: str) -> str:
        # Common language mappings
        language_map = {
            'finnish': 'fi',
            'turkish': 'tr',
            'english': 'en',
            'german': 'de',
            'french': 'fr',
            'spanish': 'es',
            'swedish': 'sv',
            'norwegian': 'no',
            'danish': 'da',
            'italian': 'it',
            'portuguese': 'pt',
            'russian': 'ru',
            'arabic': 'ar',
            'chinese': 'zh',
            'japanese': 'ja',
            'korean': 'ko',
        }

        # Check if it's already a code
        if len(language_name) == 2:
            return language_name

        # Try to map from name
        return language_map.get(language_name.lower(), language_name[:2].lower())

    def process_translation_file(
        self,
        input_file: Path,
        output_dir: Optional[Path] = None,
        engine: Optional[str] = None,
        preview: bool = False,
        keep_individual: bool = False
    ) -> bool:
        # Parse translation file
        try:
            translations = self.parser.parse_file(input_file)
        except Exception as e:
            console.print(f"[red]Error parsing file: {e}[/red]")
            return False

        # Validate consistency
        if not self.parser.validate_consistency(translations):
            console.print("[yellow]Warning: Inconsistent languages in translations[/yellow]")

        # Get languages
        languages = self.parser.get_languages(translations)
        if len(languages) < 2:
            console.print(f"[red]Error: File must contain at least 2 languages. Found: {languages}[/red]")
            return False

        # Setup output
        if not output_dir:
            output_dir = Path(self.config.get("output", {}).get("directory", "./output"))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate audio for each translation
        audio_pairs: List[Tuple[Path, Path]] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:

            task = progress.add_task(
                f"Processing {len(translations.translations)} translations...",
                total=len(translations.translations)
            )

            Path('./.tmp').mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=".tmp") as temp_dir:
                temp_path = Path(temp_dir)

                for i, item in enumerate(translations.translations):
                    # Generate audio for each language in the translation
                    item_dict = item.model_dump()
                    audio_paths = []
                    success_all = True

                    for lang_idx, (lang_name, text) in enumerate(item_dict.items()):
                        if text:  # Skip empty fields
                            # Map language names to codes (simplified mapping)
                            lang_code = self._get_language_code(lang_name)
                            audio_path = Path.joinpath(temp_path, f"{lang_name}_{i:03d}.mp3")

                            success = self.engine_manager.generate_with_fallback(
                                text=text,
                                language=lang_code,
                                output_path=audio_path,
                                preferred_engine=engine
                            )

                            if success:
                                audio_paths.append(audio_path)
                            else:
                                success_all = False
                                break

                    if success_all and len(audio_paths) >= 2:
                        # For now, assume first two languages are primary/secondary
                        audio_pairs.append((audio_paths[0], audio_paths[1]))
                    else:
                        console.print(f"[yellow]Warning: Failed to generate audio for item {i+1}[/yellow]")

                    progress.update(task, advance=1)

                if not audio_pairs:
                    console.print("[red]Error: No audio files were generated[/red]")
                    return False

                # Combine audio files
                # Use the input file name (without extension) as the base for the output filename
                # Fall back to the translations title if input_file is not provided
                base_name = input_file.stem if input_file else translations.metadata.title
                # Ensure it's a safe filename (replace spaces with underscores)
                safe_base_name = str(base_name).replace(" ", "_")
                engine_name = engine or self.config.get("general", {}).get("default_engine", "mixed")
                output_filename = f"{safe_base_name}_{engine_name}_{timestamp}.mp3"
                output_path = Path.joinpath(output_dir, output_filename)

                console.print(f"\n[cyan]Combining audio files...[/cyan]")
                success = self.audio_processor.process_translation_batch(
                    audio_pairs=audio_pairs,
                    output_path=output_path,
                    format="mp3",
                    keep_individual=keep_individual
                )

                if success:
                    console.print(f"[green]✓ Audio saved to: {output_path}[/green]")

                    if preview:
                        self._play_audio(output_path)

                    return True
                else:
                    console.print("[red]Error: Failed to combine audio files[/red]")
                    return False

    def _play_audio(self, audio_path: Path):
        try:
            import simpleaudio as sa

            console.print(f"[cyan]Playing: {audio_path}[/cyan]")

            # Check file extension
            if audio_path.suffix.lower() == '.mp3':
                # Convert MP3 to WAV in memory for playback
                from pydub import AudioSegment
                import io
                import wave

                # Load MP3
                audio = AudioSegment.from_mp3(str(audio_path))

                # Convert to WAV in memory
                wav_buffer = io.BytesIO()
                audio.export(wav_buffer, format="wav")
                wav_buffer.seek(0)

                # Read WAV data
                with wave.open(wav_buffer, 'rb') as wav_file:
                    audio_data = wav_file.readframes(wav_file.getnframes())
                    num_channels = wav_file.getnchannels()
                    bytes_per_sample = wav_file.getsampwidth()
                    sample_rate = wav_file.getframerate()

                # Play using simpleaudio
                wave_obj = sa.WaveObject(audio_data, num_channels, bytes_per_sample, sample_rate)
                play_obj = wave_obj.play()
                play_obj.wait_done()

            elif audio_path.suffix.lower() == '.wav':
                # For WAV files, use simpleaudio directly
                wave_obj = sa.WaveObject.from_wave_file(str(audio_path))
                play_obj = wave_obj.play()
                play_obj.wait_done()
            else:
                console.print(f"[yellow]Unsupported audio format: {audio_path.suffix}[/yellow]")

        except ImportError as e:
            console.print(f"[yellow]Missing required library: {e}[/yellow]")
            console.print(f"[yellow]Install with: pip install pydub simpleaudio[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Could not play audio: {e}[/yellow]")


@click.group()
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Text-to-Speech Learning System - Convert translations to audio"""
    setup_logging("DEBUG" if verbose else "INFO")


@cli.command()
@click.argument('input_path', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output directory')
@click.option('--engine', '-e', type=click.Choice(['edge-tts', 'gtts', 'piper', 'coqui']), help='TTS engine to use')
@click.option('--preview', '-p', is_flag=True, help='Preview audio without saving')
@click.option('--keep-individual', is_flag=True, help='Keep individual audio files')
@click.option('--lang-delay', type=float, help='Delay between languages (seconds)')
@click.option('--item-delay', type=float, help='Delay between items (seconds)')
def translate(input_path, output, engine, preview, keep_individual, lang_delay, item_delay):
    """Process a translation file or directory of translation files and generate audio"""
    processor = TTSProcessor()

    # Override timing if specified
    if lang_delay is not None:
        processor.audio_processor.between_languages_ms = int(lang_delay * 1000)
    if item_delay is not None:
        processor.audio_processor.between_items_ms = int(item_delay * 1000)

    input_path = Path(input_path)

    # Check if input is a directory or file
    if input_path.is_dir():
        # Batch processing mode
        yaml_files = sorted(input_path.glob('*.yaml')) + sorted(input_path.glob('*.yml'))

        if not yaml_files:
            console.print(f"[red]No YAML files found in directory: {input_path}[/red]")
            sys.exit(1)

        console.print(f"[cyan]Found {len(yaml_files)} YAML files to process[/cyan]")

        success_count = 0
        failed_files = []

        # Process each file
        for idx, yaml_file in enumerate(yaml_files, 1):
            success = processor.process_translation_file(
                input_file=yaml_file,
                output_dir=output,
                engine=engine,
                preview=preview,
                keep_individual=keep_individual
            )

            if success:
                success_count += 1
            else:
                failed_files.append(yaml_file.name)
                console.print(f"[red]✗ Failed to process: {yaml_file.name}[/red]")

        # Print summary
        console.print(f"\n[bold]Batch Processing Summary:[/bold]")
        console.print(f"  [green]Successful: {success_count}/{len(yaml_files)}[/green]")

        if failed_files:
            console.print(f"  [red]Failed: {len(failed_files)}[/red]")
            console.print(f"  [red]Failed files:[/red]")
            for failed_file in failed_files:
                console.print(f"    - {failed_file}")

        sys.exit(0 if success_count == len(yaml_files) else 1)

    else:
        # Single file processing mode
        success = processor.process_translation_file(
            input_file=input_path,
            output_dir=output,
            engine=engine,
            preview=preview,
            keep_individual=keep_individual
        )

        sys.exit(0 if success else 1)


@cli.command()
def list_engines():
    """List available TTS engines"""
    manager = TTSEngineManager()
    engines = manager.list_engines()

    table = Table(title="TTS Engines")
    table.add_column("Engine", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Available", justify="center")

    for engine_name, available in engines.items():
        status = "✓ Available" if available else "✗ Not Available"
        status_color = "green" if available else "red"
        table.add_row(
            engine_name,
            f"[{status_color}]{status}[/{status_color}]",
            "Yes" if available else "No"
        )

    console.print(table)


@cli.command()
@click.argument('engine', type=click.Choice(['edge-tts', 'gtts', 'piper', 'coqui']))
def test_engine(engine):
    """Test a specific TTS engine"""
    manager = TTSEngineManager()

    console.print(f"[cyan]Testing {engine}...[/cyan]")

    if manager.test_engine(engine):
        console.print(f"[green]✓ {engine} is working correctly[/green]")
    else:
        console.print(f"[red]✗ {engine} test failed[/red]")
        sys.exit(1)


@cli.command()
@click.argument('output_file', type=click.Path(path_type=Path))
def create_sample(output_file):
    """Create a sample translation file"""
    parser = TranslationParser()

    if parser.create_sample_file(output_file):
        console.print(f"[green]✓ Sample file created: {output_file}[/green]")
    else:
        console.print(f"[red]✗ Failed to create sample file[/red]")
        sys.exit(1)


@cli.command()
def test_voices():
    """Test all available voices for a given language and text"""
    import click

    # Get language
    language = click.prompt("Enter language code (e.g., fi, en, tr)", type=str)

    # Get text file
    text_file = click.prompt("Enter text file path", type=click.Path(exists=True, path_type=Path))

    # Read text from file
    try:
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
    except Exception as e:
        console.print(f"[red]Error reading text file: {e}[/red]")
        sys.exit(1)

    if not text:
        console.print("[red]Text file is empty![/red]")
        sys.exit(1)

    # Create output directory
    output_dir = Path(f"./output/voice_tests/{language}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[cyan]Testing all voices for language: {language}[/cyan]")
    console.print(f"[cyan]Output directory: {output_dir}[/cyan]")
    console.print(f"[cyan]Text: {text[:100]}{'...' if len(text) > 100 else ''}[/cyan]\n")

    # Initialize engine manager
    manager = TTSEngineManager()

    # Test each engine
    total_generated = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:

        for engine_name in manager.engines:
            # Check if engine is available
            engine = manager.engines[engine_name]
            if not engine or not engine.is_available():
                console.print(f"[yellow]Skipping {engine_name} (not available)[/yellow]")
                continue

            # Get available voices for this language
            voices = engine.get_voices(language)

            if not voices:
                console.print(f"[yellow]No voices available for {engine_name} in language {language}[/yellow]")
                continue

            # Create engine subdirectory
            engine_dir = Path.joinpath(output_dir, engine_name)
            engine_dir.mkdir(exist_ok=True)

            task = progress.add_task(
                f"Testing {engine_name} ({len(voices)} voices)...",
                total=len(voices)
            )

            for voice in voices:
                try:
                    # Generate safe filename from voice name
                    safe_voice_name = voice.replace('/', '_').replace('\\', '_').replace(':', '_')
                    output_file = Path.joinpath(engine_dir, f"{safe_voice_name}.mp3")

                    # Generate audio
                    success = engine.generate_speech(
                        text=text,
                        language=language,
                        output_path=output_file,
                        voice=voice
                    )

                    if success:
                        console.print(f"  [green]✓[/green] {engine_name}/{voice}")
                        total_generated += 1
                    else:
                        console.print(f"  [red]✗[/red] {engine_name}/{voice}")

                except Exception as e:
                    console.print(f"  [red]✗[/red] {engine_name}/{voice}: {e}")

                progress.update(task, advance=1)

    console.print(f"\n[green]✓ Generated {total_generated} audio files in: {output_dir}[/green]")


@cli.command()
def interactive():
    """Interactive mode for processing translations"""
    console.print("[bold cyan]Text-to-Speech Learning System - Interactive Mode[/bold cyan]\n")

    # Select engine
    manager = TTSEngineManager()
    available_engines = [e for e, avail in manager.list_engines().items() if avail]

    # Get input file
    input_file = click.prompt("Enter translation file path", type=click.Path(exists=True, path_type=Path))

    if not available_engines:
        console.print("[red]No TTS engines available![/red]")
        sys.exit(1)

    console.print("\n[cyan]Available engines:[/cyan]")
    for i, engine in enumerate(available_engines, 1):
        console.print(f"  {i}. {engine}")

    engine_choice = click.prompt("\nSelect engine (number)", type=int, default=1)
    engine = available_engines[engine_choice - 1] if 1 <= engine_choice <= len(available_engines) else None

    # Options
    preview = click.confirm("Preview audio after generation?", default=False)
    keep_individual = click.confirm("Keep individual audio files?", default=False)

    # Custom timing
    if click.confirm("Customize timing?", default=False):
        lang_delay = click.prompt("Delay between languages (seconds)", type=float, default=1.5)
        item_delay = click.prompt("Delay between items (seconds)", type=float, default=0.5)
    else:
        lang_delay = None
        item_delay = None

    # Process
    processor = TTSProcessor()

    if lang_delay is not None:
        processor.audio_processor.between_languages_ms = int(lang_delay * 1000)
    if item_delay is not None:
        processor.audio_processor.between_items_ms = int(item_delay * 1000)

    success = processor.process_translation_file(
        input_file=Path(input_file),
        engine=engine,
        preview=preview,
        keep_individual=keep_individual
    )

    if success:
        console.print("\n[green]✓ Processing complete![/green]")
    else:
        console.print("\n[red]✗ Processing failed![/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
