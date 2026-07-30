"""Base parser — abstract interface all document parsers must implement."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParsedPage:
    """Text extracted from a single page or slide."""
    page_number: int
    text: str
    used_ocr: bool = False           # True if Tesseract was used for this page


@dataclass
class ParsedDocument:
    """Full parsed output from any document format."""
    pages: List[ParsedPage] = field(default_factory=list)
    title: Optional[str] = None
    author: Optional[str] = None
    file_type: str = ''

    @property
    def full_text(self) -> str:
        """Concatenated text of all pages."""
        return '\n\n'.join(p.text for p in self.pages if p.text.strip())

    @property
    def ocr_page_count(self) -> int:
        return sum(1 for p in self.pages if p.used_ocr)


class BaseParser(ABC):
    """Abstract base class for all document parsers."""

    @abstractmethod
    def can_parse(self, file_type: str) -> bool:
        """Return True if this parser handles the given file_type."""
        ...

    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse the file at file_path and return a ParsedDocument.
        Raises ValueError for unsupported/corrupt files.
        """
        ...
