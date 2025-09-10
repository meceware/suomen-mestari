"""TTS Engine Manager - Handles engine selection and fallback"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml

from engines.edge_tts_engine import EdgeTTSEngine
from engines.gtts_engine import GTTSEngine
from engines.piper_engine import PiperEngine
from engines.coqui_engine import CoquiEngine

logger = logging.getLogger(__name__)


class TTSEngineManager:
    # Engine class mapping
    ENGINE_CLASSES = {
        "edge-tts": EdgeTTSEngine,
        "gtts": GTTSEngine,
        "piper": PiperEngine,
        "coqui": CoquiEngine,
    }

    def __init__(self, config = {}):
        self.config = config
        self.engines = {}
        self.available_engines = []

        # Initialize engines
        self._initialize_engines()

    def _initialize_engines(self):
        engines_config = self.config.get("engines", {})

        for engine_name, engine_class in self.ENGINE_CLASSES.items():
            engine_config = engines_config.get(engine_name, {})

            if not engine_config.get("enabled", True):
                logger.info(f"Engine {engine_name} is disabled in config")
                continue

            try:
                engine = engine_class(engine_config)
                if engine.is_available():
                    self.engines[engine_name] = engine
                    self.available_engines.append(engine_name)
                    logger.info(f"Successfully initialized {engine_name}")
                else:
                    logger.warning(f"Engine {engine_name} is not available")
            except Exception as e:
                logger.error(f"Failed to initialize {engine_name}: {e}")

    def _get_fallback_engines(self) -> List[str]:
        fallback_order = self.config.get("general", {}).get("fallback_order", [])

        # Filter to only available engines
        available_fallbacks = [
            engine for engine in fallback_order
            if engine in self.available_engines
        ]

        # Add any available engines not in fallback order
        for engine in self.available_engines:
            if engine not in available_fallbacks:
                available_fallbacks.append(engine)

        return available_fallbacks

    def generate_with_fallback(
        self,
        text: str,
        language: str,
        output_path: Path,
        preferred_engine: Optional[str] = None,
        **kwargs
    ) -> bool:
        # Build engine order
        engine_order = []

        if preferred_engine and preferred_engine in self.available_engines:
            engine_order.append(preferred_engine)

        # Add default engine
        default_engine = self.config.get("general", {}).get("default_engine")
        if default_engine and default_engine not in engine_order:
            engine_order.append(default_engine)

        # Add fallback engines
        for engine in self._get_fallback_engines():
            if engine not in engine_order:
                engine_order.append(engine)

        # Try each engine in order
        for engine_name in engine_order:
            if engine_name not in self.engines:
                continue

            engine = self.engines[engine_name]
            logger.info(f"Attempting to generate with {engine_name}")

            try:
                success = engine.generate_speech(
                    text=text,
                    language=language,
                    output_path=output_path,
                    **kwargs
                )

                if success:
                    logger.info(f"Successfully generated with {engine_name}")
                    return True
                else:
                    logger.warning(f"Failed to generate with {engine_name}")

            except Exception as e:
                logger.error(f"Error with {engine_name}: {e}")

        logger.error("All engines failed to generate speech")
        return False

    def list_engines(self) -> Dict[str, bool]:
        result = {}
        for engine_name in self.ENGINE_CLASSES:
            result[engine_name] = engine_name in self.available_engines
        return result

    def test_engine(self, engine_name: str, text: str = "Hello, this is a test.") -> bool:
        if engine_name not in self.engines:
            logger.error(f"Engine {engine_name} not available")
            return False

        import tempfile
        Path('.tmp').mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".mp3", dir=".tmp", delete=True) as tmp:
            output_path = Path(tmp.name)

            try:
                success = self.engines[engine_name].generate_speech(
                    text=text,
                    language="en",
                    output_path=output_path
                )

                # Check if file was created
                if success and output_path.exists():
                    logger.info(f"Test successful for {engine_name}")
                    return True

            except Exception as e:
                logger.error(f"Test failed for {engine_name}: {e}")

        return False
