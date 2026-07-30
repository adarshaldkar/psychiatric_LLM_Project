"""TXT parser — plain text with structure detection (ALL CAPS headings, numbered sections)."""
import re
import logging
from typing import List

from app.rag.parsers.base_parser import BaseParser, ParsedDocument, ParsedPage

logger = logging.getLogger(__name__)

# Patterns that indicate a heading in plain text
HEADING_PATTERNS = [
    re.compile(r'^[A-Z][A-Z\s]{4,}$'),           # ALL CAPS line
    re.compile(r'^\d+\.\s+[A-Z]'),                # "1. Introduction"
    re.compile(r'^\d+\.\d+\s+[A-Z]'),             # "1.2 Section"
    re.compile(r'^(Chapter|Section|Part)\s+', re.I),  # Chapter/Section prefix
    re.compile(r'^={3,}|^-{3,}|^\#{1,3}\s'),      # Markdown-style headings
]


def _is_heading(line: str) -> bool:
    return any(p.match(line.strip()) for p in HEADING_PATTERNS)


class TXTParser(BaseParser):
    def can_parse(self, file_type: str) -> bool:
        return file_type.lower() == 'txt'

    def parse(self, file_path: str) -> ParsedDocument:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                raw = f.read()
        except Exception as e:
            raise ValueError(f"Cannot read TXT file: {e}")

        # Annotate headings with markdown-style markers for the chunker
        lines = raw.splitlines()
        annotated: List[str] = []
        for line in lines:
            if _is_heading(line) and line.strip():
                annotated.append(f'\n## {line.strip()}\n')
            else:
                annotated.append(line)

        annotated_text = '\n'.join(annotated)

        # Split into virtual pages at double blank lines (natural section breaks)
        sections = re.split(r'\n{3,}', annotated_text)
        pages: List[ParsedPage] = []
        for i, section in enumerate(sections):
            text = section.strip()
            if text:
                pages.append(ParsedPage(
                    page_number=i + 1,
                    text=text,
                    used_ocr=False
                ))

        logger.info(f"TXT parsed: {len(lines)} lines → {len(pages)} sections — {file_path}")

        return ParsedDocument(pages=pages, file_type='txt')
