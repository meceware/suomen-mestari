"""Edge TTS Engine Implementation"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import edge_tts

from .base import TTSEngine

logger = logging.getLogger(__name__)

class EdgeTTSEngine(TTSEngine):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.rate = config.get("rate", "+0%")
        self.volume = config.get("volume", "+0%")
        self.pitch = config.get("pitch", "+0Hz")
        self.default_voices = config.get("voices", {})
        self._voices_cache = None

    async def _generate_speech_async(
        self,
        text: str,
        voice: str,
        output_path: Path,
        rate: str,
        volume: str,
        pitch: str,
    ) -> bool:
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume,
                pitch=pitch,
            )
            await communicate.save(str(output_path))
            return True
        except Exception as e:
            logger.error(f"Edge TTS generation failed: {e}")
            return False

    def generate_speech(
        self,
        text: str,
        language: str,
        output_path: Path,
        voice: Optional[str] = None,
        **kwargs
    ) -> bool:
        # Get voice
        if not voice:
            voice = self.get_default_voice(language)
            if not voice:
                logger.error(f"No voice available for language: {language}")
                return False

        # Get parameters
        rate = kwargs.get("rate", self.rate)
        volume = kwargs.get("volume", self.volume)
        pitch = kwargs.get("pitch", self.pitch)

        logger.info(f"Generating speech with Edge TTS: {voice}")

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Run async function
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        success = loop.run_until_complete(
            self._generate_speech_async(
                text, voice, output_path, rate, volume, pitch
            )
        )

        if success:
            logger.info(f"Successfully generated: {output_path}")
        else:
            logger.error(f"Failed to generate: {output_path}")

        return success

    def is_available(self) -> bool:
        # Edge TTS doesn't require installation check
        # It works as long as there's internet connection
        return True

    def get_voices(self, language: str) -> List[str]:
        voices = self.list_all_voices()

        # Filter voices by language code
        # The Locale field contains language-region format (e.g., 'fi-FI', 'en-US')
        matching_voices = []
        for voice in voices:
            locale = voice.get('Locale', '')
            # Check if the locale starts with the language code
            if locale.lower().startswith(f"{language.lower()}-"):
                short_name = voice.get('ShortName')
                if short_name:
                    matching_voices.append(short_name)

        return matching_voices

    def get_default_voice(self, language: str) -> Optional[str]:
        # Try to get from config voices mapping first
        config_voice = self.default_voices.get(language)
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

    def list_all_voices(self) -> List[Dict[str, Any]]:
        # Get all voices (use cached if available)
        if self._voices_cache is None:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            self._voices_cache = loop.run_until_complete(edge_tts.list_voices())

        if not self._voices_cache:
            logger.warning(f"Could not retrieve voices list")
            return []

        return self._voices_cache
