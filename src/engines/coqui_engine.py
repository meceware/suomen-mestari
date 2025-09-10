"""Coqui TTS Engine Implementation"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .base import TTSEngine

logger = logging.getLogger(__name__)

class CoquiEngine(TTSEngine):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.use_gpu = config.get("use_gpu", False)
        self.default_models = config.get("models", {})
        self._tts_models = {}
        self._models_cache = None

    def _load_model(self, model_name: str):
        try:
            from TTS.api import TTS

            if model_name not in self._tts_models:
                logger.info(f"Loading Coqui TTS model: {model_name}")
                self._tts_models[model_name] = TTS(model_name=model_name, gpu=self.use_gpu, progress_bar=False)
                logger.info(f"Model loaded successfully: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise

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

        logger.info(f"Generating speech with Coqui TTS: {voice}")

        try:
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Load model if needed
            self._load_model(voice)

            # Generate speech
            if voice in self._tts_models:
                # Create a temporary WAV file path
                temp_wav_path = output_path.with_suffix('.wav')

                # Generate WAV file
                self._tts_models[voice].tts_to_file(
                    text=text.lower(), # Without lower, generates an error with turkish for some reason!
                    file_path=str(temp_wav_path),
                    language=language if self._tts_models[voice].is_multi_lingual else None
                )

                # Convert WAV to MP3 if needed
                try:
                    from pydub import AudioSegment
                    # Load the WAV file
                    audio = AudioSegment.from_wav(str(temp_wav_path))
                    # Export as MP3
                    audio.export(str(output_path), format="mp3")
                    # Remove the temporary WAV file
                    temp_wav_path.unlink()
                    logger.info(f"Successfully generated and converted to MP3: {output_path}")
                except ImportError:
                    logger.warning("pydub not installed, keeping WAV format")
                    return False
                except Exception as e:
                    logger.error(f"Failed to convert to MP3: {e}")
                    return False
                finally:
                    temp_wav_path.unlink(missing_ok=True)

                return True
            else:
                logger.error("TTS model not loaded")
                return False

        except Exception as e:
            logger.error(f"Coqui TTS generation failed: {e}")
            return False

    def is_available(self) -> bool:
        try:
            from TTS.api import TTS
            return True
        except ImportError:
            logger.error("Coqui TTS (TTS package) not installed")
            return False
        except Exception as e:
            logger.error(f"Coqui TTS availability check failed: {e}")
            return False

    def get_voices(self, language: str) -> list:
        models = self.list_available_models()

        matching_models = []
        for model in models:
            # Only consider TTS models (not vocoders or voice conversion)
            if not isinstance(model, str) or not model.startswith('tts_models/'):
                continue

            # Parse the model path
            parts = model.split('/')
            if len(parts) >= 2:
                model_lang = parts[1]

                # If it's multilingual, accept it as language-agnostic
                if model_lang == 'multilingual':
                    matching_models.append(model)
                # Otherwise check for language match
                elif model_lang.lower() == language.lower():
                    matching_models.append(model)
                # Also check for language with country code (e.g., 'en' matches 'en_US')
                elif model_lang.lower().startswith(f"{language.lower()}_"):
                    matching_models.append(model)

        return matching_models

    def get_default_voice(self, language: str) -> Optional[str]:
        # Try to get from config voices mapping first
        config_voice = self.default_models.get(language)
        # Verify that this voice actually exists
        available_voices = self.get_voices(language)

        if config_voice:
            if config_voice in available_voices:
                return config_voice
            else:
                logger.warning(f"Configured voice '{config_voice}' not found in available voices for language '{language}'")

        # Fallback to first available voice for the language
        if available_voices:
            logger.info(f"Using fallback voice '{available_voices[0]}' for language '{language}'")
            return available_voices[0]

        logger.error(f"No voices available for language: {language}")
        return None

    def list_available_models(self) -> list:
        if self._models_cache is None:
            try:
                from TTS.api import TTS
                self._models_cache = TTS.list_models()
                # TODO: Remove bark model as it's not working properly
                self._models_cache.remove('tts_models/multilingual/multi-dataset/bark')
            except Exception as e:
                pass

        if not self._models_cache:
            logger.warning(f"Could not retrieve voices list")
            return []

        return self._models_cache
