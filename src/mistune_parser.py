"""
Improved markdown parser using mistune for extracting Finnish learning content.
Extracts content by sections without pre-processing, letting AI handle translation and separation.
"""

import os
import mistune
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
from utils import create_safe_filename

@dataclass
class ContentSection:
    """Represents a section of learning content with raw text."""
    title: str
    raw_content: str  # Raw content without pre-processing
    section_type: str   # dialogue, reading, vocabulary, exercise
    order: int         # Order in the document

class MistuneMarkdownParser:
    """Parser using mistune for robust markdown processing."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.markdown = mistune.create_markdown(renderer=None)  # Parse to AST

    def parse_file(self, filepath: str) -> List[ContentSection]:
        """
        Parse a markdown file and extract content sections.

        Args:
            filepath: Path to the markdown file

        Returns:
            List of ContentSection objects with raw content
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()

            sections = self._extract_sections(content)
            self.logger.debug(f"Extracted {len(sections)} sections from {filepath}")
            return sections

        except Exception as e:
            self.logger.error(f"Error parsing file {filepath}: {e}")
            return []

    def _extract_sections(self, content: str) -> List[ContentSection]:
        """Extract sections from markdown content using mistune."""
        sections = []

        # Parse markdown to AST
        tokens = self.markdown(content)

        current_section = None
        current_content = []
        order = 1
        main_title_content = []  # Content under main title before first ## section
        found_main_title = False

        for token in tokens:
            if token['type'] == 'heading':
                if self._is_main_title(token):
                    # This is the main title (# Kappale 6)
                    found_main_title = True
                    continue
                elif self._is_level_2_heading(token):
                    # Save main title content as first section if we have any
                    if found_main_title and main_title_content and not current_section:
                        raw_content = self._tokens_to_text(main_title_content)
                        if raw_content.strip():
                            main_title_text = self._get_main_title_from_tokens(tokens)
                            sections.append(ContentSection(
                                title=main_title_text,
                                raw_content=raw_content,
                                section_type='reading',
                                order=order
                            ))
                            order += 1

                    # Save previous section if exists
                    if current_section and current_content:
                        raw_content = self._tokens_to_text(current_content)
                        if raw_content.strip():
                            sections.append(ContentSection(
                                title=current_section,
                                raw_content=raw_content,
                                section_type=self._determine_section_type(current_section),
                                order=order
                            ))
                            order += 1

                    # Start new section
                    current_section = self._extract_heading_text(token)
                    current_content = []

            elif current_section:
                # Add content to current section
                current_content.append(token)
            elif found_main_title:
                # Add content to main title section (before first ## heading)
                main_title_content.append(token)

        # Save main title content if no ## sections were found
        if found_main_title and main_title_content and not sections:
            raw_content = self._tokens_to_text(main_title_content)
            if raw_content.strip():
                main_title_text = self._get_main_title_from_tokens(tokens)
                sections.append(ContentSection(
                    title=main_title_text,
                    raw_content=raw_content,
                    section_type='reading',
                    order=order
                ))
                order += 1

        # Don't forget the last section
        if current_section and current_content:
            raw_content = self._tokens_to_text(current_content)
            if raw_content.strip():
                sections.append(ContentSection(
                    title=current_section,
                    raw_content=raw_content,
                    section_type=self._determine_section_type(current_section),
                    order=order
                ))

        return sections

    def _is_level_2_heading(self, heading_token: Dict[str, Any]) -> bool:
        """Check if heading token is level 2 (##)."""
        # In mistune v3, we need to check the style attribute
        style = heading_token.get('style', '')
        if style == 'setext':
            # Setext style headings (underlined with = or -)
            return False  # These are usually level 1 or 2, but we want ATX style
        elif style == 'atx':
            # ATX style headings (prefixed with #)
            # We need to infer level from the original markdown
            # For now, let's check if the heading text looks like a level 2 heading
            heading_text = self._extract_heading_text(heading_token)
            # Level 2 headings in our document are like "s. 147", "Harjoitus 1", etc.
            return (heading_text.startswith('s.') or
                    heading_text.startswith('Harjoitus') or
                    heading_text.startswith('Useful'))

        # Fallback: assume it's level 2 if it's not the main title
        heading_text = self._extract_heading_text(heading_token)
        return heading_text != 'Kappale 6'

    def _extract_heading_text(self, heading_token: Dict[str, Any]) -> str:
        """Extract text from heading token."""
        if 'children' in heading_token:
            text_parts = []
            for child in heading_token['children']:
                if child['type'] == 'text':
                    text_parts.append(child['raw'])
            return ''.join(text_parts).strip()
        return heading_token.get('raw', '').strip()

    def _tokens_to_text(self, tokens: List[Dict[str, Any]]) -> str:
        """Convert tokens back to raw text content."""
        text_parts = []

        for token in tokens:
            if token['type'] == 'paragraph':
                # Extract text from paragraph
                if 'children' in token:
                    for child in token['children']:
                        if child['type'] == 'text':
                            text_parts.append(child['raw'])
                text_parts.append('\n\n')

            elif token['type'] == 'block_code':
                # Preserve code blocks as-is
                text_parts.append('```\n')
                text_parts.append(token['raw'])
                text_parts.append('\n```\n\n')

            elif token['type'] == 'list':
                # Handle lists
                text_parts.append(self._process_list(token))
                text_parts.append('\n\n')

            elif token['type'] == 'heading':
                # Handle sub-headings
                level = '#' * token.get('level', 1)
                heading_text = self._extract_heading_text(token)
                text_parts.append(f"{level} {heading_text}\n\n")

            elif hasattr(token, 'raw'):
                # Fallback: use raw content if available
                text_parts.append(token['raw'])
                text_parts.append('\n')

        return ''.join(text_parts)

    def _process_list(self, list_token: Dict[str, Any]) -> str:
        """Process list tokens to text."""
        list_text = []

        if 'children' in list_token:
            for item in list_token['children']:
                if item['type'] == 'list_item':
                    item_text = self._process_list_item(item)
                    list_text.append(f"- {item_text}")

        return '\n'.join(list_text)

    def _process_list_item(self, item_token: Dict[str, Any]) -> str:
        """Process list item token to text."""
        if 'children' in item_token:
            text_parts = []
            for child in item_token['children']:
                if child['type'] == 'paragraph' and 'children' in child:
                    for grandchild in child['children']:
                        if grandchild['type'] == 'text':
                            text_parts.append(grandchild['raw'])
                elif child['type'] == 'text':
                    text_parts.append(child['raw'])
            return ''.join(text_parts)
        return item_token.get('raw', '')

    def _is_main_title(self, heading_token: Dict[str, Any]) -> bool:
        """Check if heading token is the main title (# Kappale 6)."""
        heading_text = self._extract_heading_text(heading_token)
        return heading_text.startswith('Kappale') or heading_text.startswith('Chapter')

    def _get_main_title_from_tokens(self, tokens: List[Dict[str, Any]]) -> str:
        """Extract the main title from tokens."""
        for token in tokens:
            if token['type'] == 'heading' and self._is_main_title(token):
                return self._extract_heading_text(token)
        return "Introduction"  # Fallback

    def _determine_section_type(self, title: str) -> str:
        """Determine the type of section based on title."""
        title_lower = title.lower()

        # Check for exercises
        if 'harjoitus' in title_lower or 'exercise' in title_lower:
            return 'exercise'

        # Check for page sections
        if title_lower.startswith('s.') or 'page' in title_lower:
            return 'reading'

        # Check for useful phrases
        if 'phrase' in title_lower or 'useful' in title_lower:
            return 'vocabulary'

        # Default to reading
        return 'reading'

    def create_filename(self, section: ContentSection, base_name: str) -> str:
        """Create a descriptive filename for the audio file."""
        # Extract base name from file (e.g., 'kappale-6' from 'kappale-6.md')
        base = base_name.replace('.md', '')

        # Create safe title
        safe_title = create_safe_filename(section.title)

        # Format: kappale-6_01_title.mp3
        filename = os.path.join(base, f"{section.order:02d}-{safe_title}")

        return filename
