"""
Text-to-Speech generator supporting both Piper TTS and Edge TTS for Finnish and English audio generation.
"""

import os
import tempfile
import logging
import io
import asyncio
from typing import Optional, List
from pathlib import Path
import wave
from pydub import AudioSegment
from utils import get_config

class TTSGenerator:
    """TTS generator supporting multiple engines (Piper and Edge TTS)."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Get TTS engine selection
        self.tts_engine = get_config('TTS_ENGINE', 'piper').lower()

        # Get voice configurations for both engines
        self.piper_finnish_voice = get_config('PIPER_VOICE_FI', 'fi_FI-harri-medium')
        self.piper_english_voice = get_config('PIPER_VOICE_EN', 'en_US-lessac-medium')
        self.edge_finnish_voice = get_config('EDGE_VOICE_FI', 'fi-FI-HarriNeural')
        self.edge_english_voice = get_config('EDGE_VOICE_EN', 'en-US-JennyNeural')

        self.sample_rate = int(get_config('SAMPLE_RATE', '22050'))
        self.pause_duration = float(get_config('PAUSE_DURATION', '2.0'))

        # Model directory for Piper
        self.models_dir = Path('./models')
        self.models_dir.mkdir(exist_ok=True)

        # Initialize the selected TTS engine
        self._initialize_tts_engine()

    def _initialize_tts_engine(self):
        """Initialize the selected TTS engine."""
        self.logger.info(f"Initializing TTS engine: {self.tts_engine}")

        if self.tts_engine == 'edge':
            self._check_edge_installation()
            self.logger.info(f"Edge TTS voices - Finnish: {self.edge_finnish_voice}, English: {self.edge_english_voice}")
        elif self.tts_engine == 'piper':
            self._check_piper_installation()
            self._ensure_voice_models()
            self.logger.info(f"Piper TTS voices - Finnish: {self.piper_finnish_voice}, English: {self.piper_english_voice}")
        else:
            self.logger.warning(f"Unknown TTS engine: {self.tts_engine}, falling back to Piper")
            self.tts_engine = 'piper'
            self._check_piper_installation()
            self._ensure_voice_models()

    def _check_edge_installation(self) -> bool:
        """Check if Edge TTS is installed and available."""
        try:
            import edge_tts
            self.logger.debug("Edge TTS is available")
            return True
        except ImportError:
            self.logger.error("Edge TTS not installed. Please install with: pip install edge-tts")
            return False
        except Exception as e:
            self.logger.error(f"Error checking Edge TTS installation: {e}")
            return False

    def _check_piper_installation(self) -> bool:
        """Check if Piper TTS is installed and available."""
        try:
            # Try to import PiperVoice to check if Piper is available
            from piper import PiperVoice
            self.logger.debug("Piper TTS Python API is available")
            return True
        except ImportError:
            self.logger.error("Piper TTS not installed. Please install with: pip install piper-tts")
            return False
        except Exception as e:
            self.logger.error(f"Error checking Piper installation: {e}")
            return False

    def _ensure_voice_models(self):
        """Check for voice models and download if needed."""
        voices_to_check = [
            (self.piper_finnish_voice, 'Finnish'),
            (self.piper_english_voice, 'English')
        ]

        for voice_name, language in voices_to_check:
            model_path = self.models_dir / f"{voice_name}.onnx"
            config_path = self.models_dir / f"{voice_name}.onnx.json"

            if not model_path.exists() or not config_path.exists():
                self.logger.info(f"Downloading {language} voice model: {voice_name}")
                self._download_voice_model(voice_name)
            else:
                self.logger.info(f"{language} voice model available: {voice_name}")

    def _download_voice_model(self, voice_name: str) -> bool:
        """Download a specific voice model using the correct Piper command."""
        try:
            import subprocess

            # Use the correct download command
            cmd = [
                'python3', '-m', 'piper.download_voices', voice_name,
                '--data-dir', str(self.models_dir)
            ]

            self.logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                self.logger.info(f"Successfully downloaded voice model: {voice_name}")
                return True
            else:
                self.logger.error(f"Failed to download voice model {voice_name}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout downloading voice model: {voice_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error downloading voice model {voice_name}: {e}")
            return False

    def generate_speech(self, text: str, language: str = 'fi') -> Optional[AudioSegment]:
        """
        Generate speech audio from text using the selected TTS engine.

        Args:
            text: Text to convert to speech
            language: Language code ('fi' for Finnish, 'en' for English)

        Returns:
            AudioSegment object or None if generation fails
        """
        if not text or not text.strip():
            return None

        try:
            if self.tts_engine == 'edge':
                return self._generate_edge_speech(text, language)
            elif self.tts_engine == 'piper':
                return self._generate_piper_speech(text, language)
            else:
                self.logger.error(f"Unknown TTS engine: {self.tts_engine}")
                return None
        except Exception as e:
            self.logger.error(f"Speech generation failed: {e}")
            return self._generate_placeholder_audio(text, language)

    def _generate_edge_speech(self, text: str, language: str) -> Optional[AudioSegment]:
        """Generate speech using Edge TTS."""
        try:
            import edge_tts

            # Select voice based on language
            voice = self.edge_finnish_voice if language == 'fi' else self.edge_english_voice

            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name

            # Generate speech using Edge TTS
            async def generate():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(temp_path)

            # Run the async function
            asyncio.run(generate())

            # Load the generated audio file
            audio = AudioSegment.from_mp3(temp_path)

            # Clean up temporary file
            os.unlink(temp_path)

            self.logger.debug(f"Generated Edge TTS audio for: {text[:50]}... using voice: {voice}")
            return audio

        except Exception as e:
            self.logger.error(f"Edge TTS generation failed: {e}")
            return None

    def _generate_piper_speech(self, text: str, language: str) -> Optional[AudioSegment]:
        """Generate speech using Piper TTS."""
        voice_name = self.piper_finnish_voice if language == 'fi' else self.piper_english_voice

        try:
            # Try to use actual Piper TTS
            model_path = self.models_dir / f"{voice_name}.onnx"

            if model_path.exists():
                from piper import PiperVoice

                # Use actual Piper TTS
                voice = PiperVoice.load(str(model_path))

                # Generate audio - Piper returns AudioChunk objects
                audio_chunks = list(voice.synthesize(text))

                # Extract audio bytes from AudioChunk objects
                audio_bytes = b''.join(chunk.audio_int16_bytes for chunk in audio_chunks)

                # Convert to AudioSegment
                audio = AudioSegment(
                    audio_bytes,
                    frame_rate=voice.config.sample_rate,
                    sample_width=2,  # 16-bit
                    channels=1
                )

                self.logger.debug(f"Generated Piper TTS audio for: {text[:50]}...")
                return audio

            else:
                # Fallback to placeholder audio
                self.logger.debug(f"Model not found, using placeholder for: {voice_name}")
                return self._generate_placeholder_audio(text, language)

        except Exception as e:
            self.logger.warning(f"Piper TTS failed, using placeholder: {e}")
            return self._generate_placeholder_audio(text, language)

    def _generate_placeholder_audio(self, text: str, language: str) -> Optional[AudioSegment]:
        """Generate placeholder audio when Piper TTS is not available."""
        try:
            # Create a simple tone as placeholder
            # Duration based on text length (roughly 100ms per character)
            duration_ms = max(1000, len(text.strip()) * 100)

            # Different frequencies for different languages
            frequency = 440 if language == 'fi' else 523  # A4 vs C5

            # Generate a simple sine wave
            import numpy as np
            sample_rate = self.sample_rate
            t = np.linspace(0, duration_ms/1000, int(sample_rate * duration_ms/1000))
            wave_data = np.sin(2 * np.pi * frequency * t) * 0.3  # Lower volume

            # Convert to 16-bit PCM
            wave_data = (wave_data * 32767).astype(np.int16)

            # Create AudioSegment from numpy array
            audio = AudioSegment(
                wave_data.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,  # 16-bit
                channels=1
            )

            self.logger.debug(f"Generated placeholder audio for: {text[:50]}... ({duration_ms}ms)")
            return audio

        except Exception as e:
            self.logger.error(f"Error generating placeholder audio: {e}")
            return None

    def create_sentence_pair_audio(self, sentence_pairs: List[dict]) -> Optional[AudioSegment]:
        """
        Create learning audio for multiple sentence pairs.
        Each pair: Finnish -> pause -> English -> longer pause -> next pair

        Args:
            sentence_pairs: List of dicts with 'finnish' and 'english' keys

        Returns:
            Combined AudioSegment or None if generation fails
        """
        try:
            if not sentence_pairs:
                self.logger.warning("No sentence pairs provided")
                return None

            audio_segments = []
            pause_ms = int(self.pause_duration * 1000)  # Convert to milliseconds

            pause = AudioSegment.silent(duration=pause_ms)

            for i, pair in enumerate(sentence_pairs):
                finnish_text = pair.get('finnish', '').strip()
                english_text = pair.get('english', '').strip()

                if not finnish_text or not english_text:
                    self.logger.warning(f"Skipping invalid pair {i+1}: FI='{finnish_text}', EN='{english_text}'")
                    continue

                self.logger.debug(f"Processing pair {i+1}/{len(sentence_pairs)}: '{finnish_text}' -> '{english_text}'")

                # Generate Finnish speech
                finnish_audio = self.generate_speech(finnish_text, 'fi')
                if not finnish_audio:
                    self.logger.error(f"Failed to generate Finnish audio for: {finnish_text}")
                    continue

                # Generate English speech
                english_audio = self.generate_speech(english_text, 'en')
                if not english_audio:
                    self.logger.error(f"Failed to generate English audio for: {english_text}")
                    continue

                # Add Finnish + pause + English
                audio_segments.append(finnish_audio)
                audio_segments.append(pause)
                audio_segments.append(english_audio)

                # Add longer pause between pairs (except for the last pair)
                if i < len(sentence_pairs) - 1:
                    audio_segments.append(pause)

            if not audio_segments:
                self.logger.error("No valid audio segments generated")
                return None

            # Combine all segments
            combined_audio = sum(audio_segments)

            total_duration = len(combined_audio)
            self.logger.info(f"Created sentence pair audio: {len(sentence_pairs)} pairs, {total_duration}ms total")

            return combined_audio

        except Exception as e:
            self.logger.error(f"Error creating sentence pair audio: {e}")
            return None

    def save_audio(self, audio: AudioSegment, output_path: str) -> bool:
        """
        Save audio to file.

        Args:
            audio: AudioSegment to save
            output_path: Path to save the audio file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Export as MP3
            audio.export(output_path, format="mp3", bitrate="128k")

            self.logger.info(f"Saved audio to: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving audio to {output_path}: {e}")
            return False

    def is_available(self) -> bool:
        """Check if TTS system is ready to use."""
        if self.tts_engine == 'edge':
            return self._check_edge_installation()
        elif self.tts_engine == 'piper':
            return self._check_piper_installation()
        else:
            return False
