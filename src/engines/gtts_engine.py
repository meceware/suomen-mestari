"""Google TTS Engine Implementation"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from gtts import gTTS, lang

from .base import TTSEngine

logger = logging.getLogger(__name__)

class GTTSEngine(TTSEngine):
    def __init__(self, config: Dict[str, Any]):
        """Initialize gTTS engine"""
        super().__init__(config)
        self.slow = config.get("slow", False)
        self.tld = config.get("tld", "com")

    def generate_speech(
        self,
        text: str,
        language: str,
        output_path: Path,
        voice: Optional[str] = None,
        **kwargs
    ) -> bool:
        lang_code = self._get_language_code(language)
        if not lang_code:
            logger.error(f"Unsupported language: {language}")
            return False

        # Get parameters
        slow = kwargs.get("slow", self.slow)
        tld = kwargs.get("tld", self.tld)

        logger.info(f"Generating speech with gTTS: {lang_code}")

        try:
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate speech
            tts = gTTS(text=text, lang=lang_code, slow=slow, tld=tld)

            # Save to file
            tts.save(str(output_path))

            logger.info(f"Successfully generated: {output_path}")
            return True

        except Exception as e:
            logger.error(f"gTTS generation failed: {e}")
            return False

    def is_available(self) -> bool:
        # gTTS requires internet connection
        # We'll assume it's available if the module is installed
        return True

    def get_voices(self, language: str) -> list:
        lang_code = self._get_language_code(language)
        return [f"{lang_code}"] if lang_code else []

    def _get_language_code(self, language: str) -> Optional[str]:
        # Check if gTTS supports it directly
        return language if language in lang.tts_langs() else None
