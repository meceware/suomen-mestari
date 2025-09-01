"""
Translation service using Ollama API for Finnish to English translation.
"""

import requests
import json
import logging
from typing import List, Optional, Dict
from utils import get_config

class OllamaTranslator:
    """Translator using Ollama API for Finnish to English translation."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = get_config('OLLAMA_URL', 'http://localhost:11434')
        self.model = get_config('OLLAMA_MODEL', 'gemma3:12b')

        # Ensure URL format is correct
        if not self.base_url.endswith('/'):
            self.base_url += '/'

        self.api_url = f"{self.base_url}api/generate"

    def _test_connection(self) -> bool:
        """Test connection to Ollama API."""
        try:
            response = requests.get(f"{self.base_url}api/tags", timeout=10)
            if response.status_code == 200:
                self.logger.debug(f"Successfully connected to Ollama at {self.base_url}")
                return True
            else:
                self.logger.warning(f"Ollama API returned status {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to connect to Ollama API: {e}")
            return False

    def translate_text(self, finnish_text: str) -> Optional[str]:
        """
        Translate Finnish text to English using Ollama.

        Args:
            finnish_text: Finnish text to translate

        Returns:
            English translation or None if translation fails
        """
        if not finnish_text or not finnish_text.strip():
            return None

        # Create translation prompt
        prompt = self._create_translation_prompt(finnish_text)

        try:
            response = self._call_ollama_api(prompt)
            if response:
                translation = self._extract_translation(response)
                self.logger.debug(f"Translated: '{finnish_text}' -> '{translation}'")
                return translation
            else:
                self.logger.error(f"Failed to translate: {finnish_text}")
                return None

        except Exception as e:
            self.logger.error(f"Translation error for '{finnish_text}': {e}")
            return None

    def translate_batch(self, finnish_texts: List[str]) -> List[str]:
        """
        Translate multiple Finnish texts to English.

        Args:
            finnish_texts: List of Finnish texts to translate

        Returns:
            List of English translations (empty string for failed translations)
        """
        translations = []

        for i, text in enumerate(finnish_texts):
            self.logger.info(f"Translating {i+1}/{len(finnish_texts)}: {text[:50]}...")

            translation = self.translate_text(text)
            if translation:
                translations.append(translation)
            else:
                # Use original text as fallback
                translations.append(f"[Translation failed: {text}]")

        return translations

    def _create_translation_prompt(self, finnish_text: str) -> str:
        """Create a translation prompt for Ollama."""
        prompt = f"""Translate the following Finnish text to English. Provide only the English translation, no explanations or additional text.

Finnish: {finnish_text}
English:"""

        return prompt

    def _call_ollama_api(self, prompt: str) -> Optional[str]:
        """Make API call to Ollama."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,  # Low temperature for consistent translations
                "top_p": 0.8
            }
        }

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=600,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                self.logger.error(f"Ollama API error: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            self.logger.error("Ollama API request timed out")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.error("Failed to connect to Ollama API")
            return None
        except Exception as e:
            self.logger.error(f"Ollama API request failed: {e}")
            return None

    def _extract_translation(self, response: str) -> str:
        """Extract clean translation from Ollama response."""
        if not response:
            return ""

        # Clean up the response
        translation = response.strip()

        # Remove common prefixes that might appear
        prefixes_to_remove = [
            "English:",
            "Translation:",
            "The translation is:",
            "In English:",
        ]

        for prefix in prefixes_to_remove:
            if translation.lower().startswith(prefix.lower()):
                translation = translation[len(prefix):].strip()

        # Remove quotes if the entire translation is quoted
        if translation.startswith('"') and translation.endswith('"'):
            translation = translation[1:-1]
        elif translation.startswith("'") and translation.endswith("'"):
            translation = translation[1:-1]

        return translation

    def process_content_with_ai(self, raw_content: str) -> Optional[Dict]:
        """
        Process raw content using AI to extract Finnish sentences and their translations.

        Args:
            raw_content: Raw markdown content from a section

        Returns:
            Dictionary with structured Finnish-English pairs or None if processing fails
        """
        if not raw_content or not raw_content.strip():
            return None

        prompt = f"""You are a professional Finnish to English translator. You will be provided with Finnish text. Your task is to translate each sentence within the provided text into English. The English translations should be natural, accurate, and reflect the meaning of the original Finnish.

Crucially:

* Do not include any English text within the Finnish sentences themselves. (Only provide the Finnish sentence and its English translation.)

* Do not include Markdown formatting elements like headers, bullet points, or list markers in the output. Only provide the sentence and its translation.

* The output must be a valid JSON file containing a list of objects. Each object will have two keys: "finnish" and "english". The values for these keys will be the original Finnish sentence and its corresponding English translation, respectively.

* Maintain the original sentence order from the provided Finnish text.

* Do not include imaginary words, sentences, stick to the translation only. No output is necessary other than JSON.

Content to process:
{raw_content}

Return ONLY a JSON object in this exact format:
{{
  "sentences": [
    {{
      "finnish": "Finnish sentence or phrase here",
      "english": "English translation here"
    }}
  ]
}}

If no Finnish content is found, return: {{"sentences": []}}"""

        try:
            response = self._call_ollama_api(prompt)
            if response:
                # Clean the response - remove markdown code blocks if present
                cleaned_response = self._clean_json_response(response)

                # Try to parse JSON response
                import json
                try:
                    result = json.loads(cleaned_response)
                    if 'sentences' in result and isinstance(result['sentences'], list):
                        self.logger.debug(f"AI processed {len(result['sentences'])} sentence pairs")
                        return result
                    else:
                        self.logger.error(f"Invalid JSON structure in AI response: {cleaned_response}")
                        return None
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse AI JSON response: {e}")
                    self.logger.debug(f"Raw response: {response}")
                    self.logger.debug(f"Cleaned response: {cleaned_response}")
                    return None
            else:
                self.logger.error("No response from AI")
                return None

        except Exception as e:
            self.logger.error(f"AI content processing failed: {e}")
            return None

    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response by removing markdown code blocks and other formatting."""
        if not response:
            return ""

        cleaned = response.strip()

        # Remove markdown code blocks (```json ... ``` or ``` ... ```)
        if cleaned.startswith('```'):
            # Find the first newline after ```
            first_newline = cleaned.find('\n')
            if first_newline != -1:
                # Remove the ```json or ``` line
                cleaned = cleaned[first_newline + 1:]

            # Remove the closing ```
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]

        # Remove any remaining backticks at start/end
        cleaned = cleaned.strip('`')

        # Remove common prefixes that might appear
        prefixes_to_remove = [
            "json\n",
            "JSON\n",
            "Here is the JSON:\n",
            "Here's the JSON:\n",
        ]

        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]

        return cleaned.strip()

    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        return self._test_connection()
