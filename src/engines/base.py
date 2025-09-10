"""Base TTS Engine Interface"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """Abstract base class for TTS engines"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the TTS engine with configuration.

        Args:
            config: Engine-specific configuration dictionary
        """
        self.config = config
        self.name = self.__class__.__name__.replace("Engine", "")
        logger.info(f"Initializing {self.name} engine")

    @abstractmethod
    def generate_speech(
        self,
        text: str,
        language: str,
        output_path: Path,
        voice: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Generate speech from text and save to file.

        Args:
            text: Text to convert to speech
            language: Language code (e.g., 'fi', 'tr')
            output_path: Path where the audio file should be saved
            voice: Optional voice identifier
            **kwargs: Additional engine-specific parameters

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the engine is available and properly configured.

        Returns:
            bool: True if engine can be used, False otherwise
        """
        pass

    @abstractmethod
    def get_voices(self, language: str) -> list:
        """
        Get available voices for a specific language.

        Args:
            language: Language code

        Returns:
            list: List of available voice identifiers
        """
        pass

    def get_default_voice(self, language: str) -> Optional[str]:
        """
        Get the default voice for a language.

        Args:
            language: Language code

        Returns:
            Optional[str]: Default voice identifier or None
        """
        voices = self.get_voices(language)
        return voices[0] if voices else None

    def __str__(self) -> str:
        """String representation of the engine"""
        return f"{self.name} TTS Engine"

    def __repr__(self) -> str:
        """Detailed representation of the engine"""
        return f"<{self.__class__.__name__}(config={self.config})>"
