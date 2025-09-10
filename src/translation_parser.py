"""YAML Translation File Parser"""

import logging
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, validator
import datetime

logger = logging.getLogger(__name__)

class TranslationItem(BaseModel):
    """Model for a single translation item - accepts any language fields"""
    # Allow any language fields
    class Config:
        extra = "allow"

    def __init__(self, **data):
        # Validate that at least 2 languages are provided
        if len(data) < 2:
            raise ValueError("Translation item must contain at least 2 languages")
        # Validate that all values are non-empty strings
        for key, value in data.items():
            if not value or not str(value).strip():
                raise ValueError(f"Translation text for '{key}' cannot be empty")
        super().__init__(**data)


class TranslationMetadata(BaseModel):
    """Model for translation file metadata"""
    title: str
    created: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None

    class Config:
        extra = "allow"


class TranslationFile(BaseModel):
    """Model for the entire translation file"""
    metadata: TranslationMetadata
    translations: List[TranslationItem]

    @validator('translations')
    def validate_translations_not_empty(cls, v):
        if not v:
            raise ValueError("Translations list cannot be empty")
        return v


class TranslationParser:
    """Parser for YAML translation files"""

    def __init__(self):
        pass

    def parse_file(self, file_path: Path) -> TranslationFile:
        if not file_path.exists():
            raise FileNotFoundError(f"Translation file not found: {file_path}")

        logger.info(f"Parsing translation file: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # Validate and parse using Pydantic
            translation_file = TranslationFile(**data)

            logger.info(f"Successfully parsed {len(translation_file.translations)} translations")
            return translation_file

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise ValueError(f"Invalid YAML format: {e}")
        except Exception as e:
            logger.error(f"Failed to parse translation file: {e}")
            raise ValueError(f"Failed to parse translation file: {e}")

    def get_languages(self, translation_file: TranslationFile) -> List[str]:
        languages = set()

        if translation_file.translations:
            # Get all field names from the first translation item
            first_item = translation_file.translations[0]
            for field_name in first_item.model_fields_set:
                languages.add(field_name)

        return sorted(list(languages))

    def validate_consistency(self, translation_file: TranslationFile) -> bool:
        if not translation_file.translations:
            return True

        # Get languages from first item
        first_languages = set(translation_file.translations[0].model_fields_set)

        # Check all other items
        for i, item in enumerate(translation_file.translations[1:], start=2):
            item_languages = set(item.model_fields_set)
            if item_languages != first_languages:
                logger.warning(
                    f"Inconsistent languages in item {i}: "
                    f"expected {first_languages}, got {item_languages}"
                )
                return False

        return True

    def _save_file(self, translation_file: TranslationFile, file_path: Path) -> bool:
        try:
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dict for YAML serialization
            data = {
                'metadata': translation_file.metadata.dict(),
                'translations': [item.dict() for item in translation_file.translations]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved translation file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save translation file: {e}")
            return False

    def create_sample_file(self, file_path: Path) -> bool:
        # Create sample with generic primary/secondary language structure
        sample_translations = [
            {"primary": "Hyvää huomenta", "secondary": "Good morning"},
            {"primary": "Hyvää päivää", "secondary": "Good day"},
            {"primary": "Hei", "secondary": "Hi"},
        ]

        sample_data = TranslationFile(
            metadata=TranslationMetadata(
                title="Sample Translations",
                created=str(datetime.date.today()),
                author="TTS System",
                description="Sample translation file - replace 'primary' and 'secondary' with your language names (e.g., 'finnish', 'english')"
            ),
            translations=[TranslationItem(**item) for item in sample_translations]
        )

        return self._save_file(sample_data, file_path)
