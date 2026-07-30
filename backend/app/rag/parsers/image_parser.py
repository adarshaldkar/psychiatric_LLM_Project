"""Image parser — Pillow + Tesseract OCR for PNG, JPG, JPEG."""
import logging

from app.rag.parsers.base_parser import BaseParser, ParsedDocument, ParsedPage

logger = logging.getLogger(__name__)

SUPPORTED = {'png', 'jpg', 'jpeg'}


class ImageParser(BaseParser):
    def can_parse(self, file_type: str) -> bool:
        return file_type.lower() in SUPPORTED

    def parse(self, file_path: str) -> ParsedDocument:
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            raise RuntimeError("Pillow or pytesseract not installed")

        try:
            image = Image.open(file_path)
            # Convert to RGB (handles RGBA, L, P modes)
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
        except Exception as e:
            raise ValueError(f"Cannot open image: {e}")

        try:
            text = pytesseract.image_to_string(image, lang='eng').strip()
        except Exception as e:
            raise ValueError(f"OCR failed: {e}")

        if not text:
            logger.warning(f"OCR returned empty text for image: {file_path}")

        logger.info(f"Image OCR complete: {len(text)} characters — {file_path}")

        return ParsedDocument(
            pages=[ParsedPage(page_number=1, text=text, used_ocr=True)],
            file_type=file_path.rsplit('.', 1)[-1].lower()
        )
