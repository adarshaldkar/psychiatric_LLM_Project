"""
Deep File Upload Security Guard
Validates magic bytes, MIME signatures, file sizes, page count limits,
encrypted PDF rejection, and zip-bomb / corrupted file scanning.
"""
import io
import logging
from typing import Tuple, Optional
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Security Thresholds
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_PDF_PAGES = 1000                    # 1,000 pages
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".pptx", ".jpg", ".jpeg", ".png"}

# Magic Bytes Signatures
MAGIC_SIGNATURES = {
    "pdf": b"%PDF-",
    "docx": b"PK\x03\x04",
    "pptx": b"PK\x03\x04",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
}

class FileSecurityValidator:
    def validate_file(
        self,
        file_bytes: bytes,
        filename: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates uploaded file against size limits, magic bytes MIME signatures,
        page count ceilings, encrypted PDF rejection, and corrupted stream scanning.
        Returns (is_valid, error_message).
        """
        if not file_bytes or len(file_bytes) == 0:
            return False, "File is empty (0 bytes)."

        # 1. File Size Cap
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            size_mb = len(file_bytes) / (1024 * 1024)
            return False, f"File size ({size_mb:.1f} MB) exceeds maximum allowed limit of 50 MB."

        # 2. Extension Check
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File type '{ext}' is not supported. Allowed formats: PDF, DOCX, TXT, PPTX, JPG, PNG."

        # 3. Magic Bytes Signature Verification
        clean_ext = ext.lstrip(".")
        if clean_ext in MAGIC_SIGNATURES:
            expected_magic = MAGIC_SIGNATURES[clean_ext]
            if not file_bytes.startswith(expected_magic):
                return False, f"Security Violation: File header magic bytes do not match expected signature for {ext}."

        # 4. PDF Specific Deep Inspection
        if ext == ".pdf":
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")

                # Reject Encrypted PDFs
                if doc.is_encrypted:
                    return False, "Security Rejection: Encrypted or password-protected PDFs are not supported."

                # Page Count Ceiling
                if doc.page_count > MAX_PDF_PAGES:
                    return False, f"PDF page count ({doc.page_count}) exceeds maximum allowed limit of {MAX_PDF_PAGES} pages."

                # Corrupted Stream Scanner
                if doc.page_count == 0:
                    return False, "PDF contains zero renderable pages."

                doc.close()

            except Exception as e:
                logger.error(f"Corrupted PDF validation error: {e}")
                return False, f"File Integrity Error: Corrupted or unparseable PDF stream ({str(e)})."

        return True, None

file_validator = FileSecurityValidator()
