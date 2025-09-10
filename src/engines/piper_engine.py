"""Piper TTS Engine Implementation"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from pydub import AudioSegment

from .base import TTSEngine

logger = logging.getLogger(__name__)


class PiperEngine(TTSEngine):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.length_scale = config.get("length_scale", 1.0)
        self.model_path = Path(config.get("model_path", "./.piper")).expanduser()
        self.default_models = config.get("models", {})

    def generate_speech(
        self,
        text: str,
        language: str,
        output_path: Path,
        voice: Optional[str] = None,
        **kwargs
    ) -> bool:
        # Get model
        if not voice:
            voice = self.get_default_voice(language)
            if not voice:
                logger.error(f"No model available for language: {language}")
                return False

        # Ensure the voice model is downloaded
        if not self._ensure_voice_model(voice):
            logger.error(f"Failed to ensure voice model: {voice}")
            return False

        # Get model path
        model_path = self.model_path.joinpath(f"{voice}.onnx")

        logger.info(f"Generating speech with Piper TTS: {voice}")

        try:
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Try to use Piper Python API first
            if model_path.exists():
                from piper import PiperVoice

                # Load the voice model
                piper_voice = PiperVoice.load(str(model_path))

                # Generate audio - Piper returns AudioChunk objects
                audio_chunks = list(piper_voice.synthesize(text))

                # Extract audio bytes from AudioChunk objects
                audio_bytes = b''.join(chunk.audio_int16_bytes for chunk in audio_chunks)

                # Convert to AudioSegment
                audio = AudioSegment(
                    audio_bytes,
                    frame_rate=piper_voice.config.sample_rate,
                    sample_width=2,
                    channels=1
                )
                audio.export(str(output_path), format="mp3")

                logger.info(f"Successfully generated using Piper API: {output_path}")
                return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Piper CLI execution failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Piper generation failed: {e}")

        return False

    def is_available(self) -> bool:
        try:
            # Try to import PiperVoice to check if Piper is available
            from piper import PiperVoice
            logger.debug("Piper TTS Python API is available")
            return True
        except ImportError:
            logger.error("Piper TTS not installed. Please install with: pip install piper-tts")
            return False
        except Exception as e:
            logger.error(f"Error checking Piper installation: {e}")
            return False

    def get_voices(self, language: str) -> list:
        try:
            cmd = ['python3', '-m', 'piper.download_voices']

            logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # Parse the output - each line is a voice model
                all_voices = result.stdout.strip().split('\n')

                # Filter voices by language code
                # Piper voice format is typically: language_COUNTRY-name-quality
                matching_voices = []
                for voice in all_voices:
                    # Check if voice starts with the language code
                    if voice.startswith(f"{language}_"):
                        matching_voices.append(voice)

                if matching_voices:
                    logger.debug(f"Found {len(matching_voices)} voices for language '{language}'")
                else:
                    logger.warning(f"No voices found for language '{language}'")

                return matching_voices
            else:
                logger.error(f"Failed to list voices: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            logger.error("Timeout listing voice models")
            return []
        except FileNotFoundError:
            logger.error("Piper module not found. Using fallback voice list.")
            return []
        except Exception as e:
            logger.error(f"Error listing voice models: {e}")
            return []

    def get_default_voice(self, language: str) -> Optional[str]:
        # Try to get from config models mapping first
        config_model = self.default_models.get(language)
        # Available models
        available_models = self.get_voices(language)

        if config_model:
            # Verify that this model actually exists
            if config_model in available_models:
                return config_model
            else:
                logger.warning(f"Configured model '{config_model}' not found in available models for language '{language}'")

        # Fallback to first available model for the language
        if available_models:
            logger.info(f"Using fallback model '{available_models[0]}' for language '{language}'")
            return available_models[0]

        logger.error(f"No models available for language: {language}")
        return None

    def _ensure_voice_model(self, voice_name: str) -> bool:
        model_path = self.model_path.joinpath(f"{voice_name}.onnx")
        config_path = self.model_path.joinpath(f"{voice_name}.onnx.json")

        if model_path.exists() and config_path.exists():
            logger.debug(f"Voice model already available: {voice_name}")
            return True

        logger.info(f"Voice model not found, downloading: {voice_name}")
        return self._download_voice_model(voice_name)

    def _download_voice_model(self, voice_name: str) -> bool:
        try:
            # Create models directory if it doesn't exist
            self.model_path.mkdir(parents=True, exist_ok=True)

            # Use the correct download command
            cmd = [
                'python3', '-m', 'piper.download_voices', voice_name,
                '--data-dir', str(self.model_path)
            ]

            logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                logger.info(f"Successfully downloaded voice model: {voice_name}")
                return True
            else:
                logger.error(f"Failed to download voice model {voice_name}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout downloading voice model: {voice_name}")
            return False
        except FileNotFoundError:
            logger.error("Piper module not found. Cannot download voice models.")
            return False
        except Exception as e:
            logger.error(f"Error downloading voice model {voice_name}: {e}")
            return False
