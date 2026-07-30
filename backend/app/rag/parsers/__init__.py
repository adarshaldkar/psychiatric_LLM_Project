"""Parser registry — auto-selects the correct parser by file type."""
from app.rag.parsers.base_parser import BaseParser, ParsedDocument
from app.rag.parsers.pdf_parser import PDFParser
from app.rag.parsers.docx_parser import DOCXParser
from app.rag.parsers.txt_parser import TXTParser
from app.rag.parsers.pptx_parser import PPTXParser
from app.rag.parsers.image_parser import ImageParser

SUPPORTED_TYPES = {'pdf', 'docx', 'txt', 'pptx', 'png', 'jpg', 'jpeg'}

_PARSERS: list[BaseParser] = [
    PDFParser(),
    DOCXParser(),
    TXTParser(),
    PPTXParser(),
    ImageParser(),
]


def get_parser(file_type: str) -> BaseParser:
    """Return the correct parser for the given file extension."""
    ft = file_type.lower().lstrip('.')
    for parser in _PARSERS:
        if parser.can_parse(ft):
            return parser
    raise ValueError(
        f"Unsupported file type: '{ft}'. "
        f"Supported formats: {', '.join(sorted(SUPPORTED_TYPES))}"
    )


def parse_document(file_path: str, file_type: str) -> ParsedDocument:
    """Convenience function: get parser and parse in one call."""
    parser = get_parser(file_type)
    return parser.parse(file_path)
