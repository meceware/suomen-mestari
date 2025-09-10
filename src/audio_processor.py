"""Audio Processing Module for combining TTS outputs with timing"""

import logging
from pathlib import Path
from typing import List, Tuple, Optional
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, config: dict):
        timing_config = config.get("timing", {})
        quality_config = config.get("quality", {})

        # Timing settings (in milliseconds)
        self.between_languages_ms = int(timing_config.get("between_languages", 1.5) * 1000)
        self.between_items_ms = int(timing_config.get("between_items", 0.5) * 1000)

        # Quality settings
        self.bitrate = quality_config.get("bitrate", "192k")
        self.sample_rate = quality_config.get("sample_rate", 44100)
        self.channels = quality_config.get("channels", 1)

    def _create_silence(self, duration_ms: int) -> AudioSegment:
        return AudioSegment.silent(duration=duration_ms)

    def _load_audio(self, file_path: Path) -> Optional[AudioSegment]:
        try:
            if not file_path.exists():
                logger.error(f"Audio file not found: {file_path}")
                return None

            # Detect format from extension
            format_ext = file_path.suffix.lower().replace('.', '')
            if format_ext == 'mp3':
                audio = AudioSegment.from_mp3(file_path)
            elif format_ext == 'wav':
                audio = AudioSegment.from_wav(file_path)
            elif format_ext == 'ogg':
                audio = AudioSegment.from_ogg(file_path)
            else:
                # Try to auto-detect
                audio = AudioSegment.from_file(file_path)

            logger.info(f"Loaded audio: {file_path}")
            return audio

        except Exception as e:
            logger.error(f"Failed to load audio {file_path}: {e}")
            return None

    def _combine_translation_pair(
        self,
        main_audio_path: Path,
        second_audio_path: Path,
        add_item_silence: bool = True
    ) -> Optional[AudioSegment]:
        # Load audio files
        main_audio = self._load_audio(main_audio_path)
        second_audio = self._load_audio(second_audio_path)

        if not main_audio or not second_audio:
            logger.error("Failed to load one or both audio files")
            return None

        # Create combined audio with timing
        combined = AudioSegment.empty()

        # Add main audio
        combined += main_audio

        # Add silence between languages
        combined += self._create_silence(self.between_languages_ms)

        # Add second audio
        combined += second_audio

        # Add silence between items (if not the last item)
        if add_item_silence:
            combined += self._create_silence(self.between_items_ms)

        return combined

    def _combine_multiple_pairs(
        self,
        audio_pairs: List[Tuple[Path, Path]]
    ) -> Optional[AudioSegment]:
        if not audio_pairs:
            logger.error("No audio pairs provided")
            return None

        combined = AudioSegment.empty()
        total_pairs = len(audio_pairs)

        for i, (main_path, second_path) in enumerate(audio_pairs):
            # Don't add item silence after the last pair
            add_item_silence = (i < total_pairs - 1)

            pair_audio = self._combine_translation_pair(
                main_path,
                second_path,
                add_item_silence
            )

            if pair_audio:
                combined += pair_audio
                logger.info(f"Combined pair {i+1}/{total_pairs}")
            else:
                logger.warning(f"Failed to combine pair {i+1}: {main_path}, {second_path}")

        return combined if len(combined) > 0 else None

    def _save_audio(
        self,
        audio: AudioSegment,
        output_path: Path,
        format: str = "mp3"
    ) -> bool:
        try:
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Apply quality settings
            audio = audio.set_frame_rate(self.sample_rate)
            audio = audio.set_channels(self.channels)

            # Export with format-specific parameters
            export_params = {
                "format": format,
            }

            if format == "mp3":
                export_params["bitrate"] = self.bitrate
                export_params["parameters"] = ["-q:a", "0"]  # Highest quality
            elif format == "ogg":
                export_params["bitrate"] = self.bitrate

            audio.export(output_path, **export_params)

            logger.info(f"Saved audio: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return False

    def process_translation_batch(
        self,
        audio_pairs: List[Tuple[Path, Path]],
        output_path: Path,
        format: str = "mp3",
        keep_individual: bool = False
    ) -> bool:
        logger.info(f"Processing {len(audio_pairs)} translation pairs")

        # Combine all pairs
        combined_audio = self._combine_multiple_pairs(audio_pairs)

        if not combined_audio:
            logger.error("Failed to combine audio pairs")
            return False

        # Save combined audio
        success = self._save_audio(combined_audio, output_path, format)

        # Clean up individual files if requested
        if success and not keep_individual:
            for main_path, second_path in audio_pairs:
                try:
                    main_path.unlink(missing_ok=True)
                    second_path.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {e}")

        return success
