"""PDF parser — per-page hybrid (PyMuPDF text + EasyOCR fallback).

For each page:
  - If selectable text exists  → use PyMuPDF (fast, zero cost)
  - If image-only page         → use EasyOCR (pure Python, no system binary needed)
  - EasyOCR reader is lazy-loaded and cached — model loads only ONCE per server start.
"""
import logging
from typing import List, Optional

import fitz  # PyMuPDF

from app.rag.parsers.base_parser import BaseParser, ParsedDocument, ParsedPage

logger = logging.getLogger(__name__)

# Minimum characters to consider a page as "has selectable text"
TEXT_THRESHOLD = 30

# Lazy-loaded EasyOCR reader — cached so model weights load only once
_easyocr_reader = None


def _get_ocr_reader():
    """Load the EasyOCR reader once and reuse across all pages / documents."""
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            logger.info("Loading EasyOCR model (first load — downloads ~100 MB if not cached)...")
            print("[OCR] Loading EasyOCR model... (this takes ~10-20s on first run)")
            _easyocr_reader = easyocr.Reader(
                ['en'],
                gpu=False,    # CPU mode — no CUDA required
                verbose=False
            )
            logger.info("EasyOCR model loaded and ready.")
            print("[OCR] EasyOCR model loaded successfully!")
        except ImportError:
            logger.error("easyocr is not installed. Run: pip install easyocr")
            print("[OCR] ERROR: easyocr not installed. Run: pip install easyocr")
        except Exception as e:
            logger.error(f"Failed to load EasyOCR: {e}")
            print(f"[OCR] ERROR loading EasyOCR: {e}")
    return _easyocr_reader


class PDFParser(BaseParser):
    def can_parse(self, file_type: str) -> bool:
        return file_type.lower() == 'pdf'

    def parse(self, file_path: str) -> ParsedDocument:
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise ValueError(f"Cannot open PDF: {e}")

        # Try to extract author/title from PDF metadata
        meta   = doc.metadata or {}
        title  = meta.get('title') or None
        author = meta.get('author') or None

        pages: List[ParsedPage] = []
        ocr_page_numbers: List[int] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text('text').strip()

            if len(text) >= TEXT_THRESHOLD:
                # ── Selectable text exists → use PyMuPDF (fast) ─────────
                pages.append(ParsedPage(
                    page_number=page_num + 1,
                    text=text,
                    used_ocr=False
                ))
            else:
                # ── Image-only page → EasyOCR ────────────────────────────
                ocr_text = self._ocr_page_easyocr(page)
                ocr_page_numbers.append(page_num + 1)
                pages.append(ParsedPage(
                    page_number=page_num + 1,
                    text=ocr_text,
                    used_ocr=True
                ))

        doc.close()

        ocr_count = len(ocr_page_numbers)
        if ocr_count:
            print(f"[PDF] {len(pages)} pages | {ocr_count} image-only pages OCR'd: {ocr_page_numbers[:10]}{'...' if ocr_count > 10 else ''}")
            logger.info(f"PDF parsed: {len(pages)} pages, {ocr_count} via EasyOCR — {file_path}")
        else:
            print(f"[PDF] {len(pages)} pages — all embedded text, no OCR needed")
            logger.info(f"PDF parsed: {len(pages)} pages (all text) — {file_path}")

        return ParsedDocument(
            pages=pages,
            title=title,
            author=author,
            file_type='pdf'
        )

    def _ocr_page_easyocr(self, page) -> str:
        """Convert a PDF page to image and run EasyOCR (pure Python, no system install)."""
        try:
            import numpy as np

            reader = _get_ocr_reader()
            if reader is None:
                logger.warning(f"OCR reader unavailable — skipping page {page.number + 1}")
                return ''

            # Render page at 200 DPI (good quality / speed balance for EasyOCR)
            mat = fitz.Matrix(200 / 72, 200 / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)

            # Convert to numpy array (EasyOCR accepts numpy arrays directly)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )

            # paragraph=True merges nearby text blocks into paragraphs
            results = reader.readtext(img_array, detail=0, paragraph=True)
            text = '\n'.join(results).strip()

            if text:
                print(f"[OCR] Page {page.number + 1}: extracted {len(text)} chars via EasyOCR")
            else:
                print(f"[OCR] Page {page.number + 1}: no text found (blank/diagram page)")

            return text

        except Exception as e:
            logger.warning(f"OCR failed for page {page.number + 1}: {e}")
            print(f"[OCR] Page {page.number + 1}: failed — {e}")
            return ''
