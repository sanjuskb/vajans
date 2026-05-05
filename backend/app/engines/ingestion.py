"""
VAJANS — Document Ingestion Engine (Phase 2)
=============================================
Converts uploaded files (digital PDF, scanned PDF, images)
into structured text + RAG-ready chunks.

Pipeline:
    file_path → detect type → extract text → clean → chunk → ExtractedDocument

Author: VAJANS Team
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
import structlog
from pdf2image import convert_from_path
from PIL import Image

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

logger = structlog.get_logger("vajans.ingestion")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Text density threshold: if a PDF page has fewer characters than this
# per page on average, treat it as scanned.
DIGITAL_TEXT_DENSITY_THRESHOLD = 50   # chars per page

# Chunking
CHUNK_SIZE_CHARS = 500     # ~125 tokens — one paragraph per chunk
CHUNK_OVERLAP_CHARS = 100  # ~25 tokens overlap

# OCR
TESSERACT_CONFIG = r"--oem 3 --psm 6"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DocumentKind(str, Enum):
    DIGITAL = "digital"
    SCANNED = "scanned"
    IMAGE   = "image"


# ---------------------------------------------------------------------------
# Internal data classes
# ---------------------------------------------------------------------------

@dataclass
class PageText:
    page_number: int        # 1-indexed
    text: str
    ocr_confidence: float = 1.0   # 1.0 for digital; Tesseract avg for scanned


@dataclass
class ExtractionWarning:
    code: str
    message: str
    page: Optional[int] = None


@dataclass
class ExtractedDocument:
    """
    Output contract of the ingestion engine.
    Matches shared.contracts.schemas.ExtractedDocument semantics.
    """
    file_id:          uuid.UUID
    job_id:           uuid.UUID
    file_type:        str                        # "tender" | "bidder_document"
    document_kind:    DocumentKind
    raw_text:         str                        # full concatenated text
    page_texts:       dict[int, str]             # page_number → text
    chunks:           list[str]                  # RAG-ready chunks
    ocr_quality_score: float                     # 0.0 – 1.0
    page_count:       int
    char_count:       int
    chunk_count:      int
    warnings:         list[ExtractionWarning] = field(default_factory=list)
    extracted_at:     datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ---------------------------------------------------------------------------
# Step 1 — File type detection
# ---------------------------------------------------------------------------

def detect_document_kind(file_path: Path) -> DocumentKind:
    """
    Determine whether the PDF contains selectable text (digital)
    or is a scanned image-only PDF.

    Heuristic: open the PDF, sample up to 5 pages, count average
    characters per page. Below threshold → scanned.
    """
    suffix = file_path.suffix.lower()
    if suffix in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"):
        return DocumentKind.IMAGE

    if suffix != ".pdf":
        raise IngestionError(
            f"Unsupported file type: {suffix}",
            code="UNSUPPORTED_FILE_TYPE",
        )

    try:
        doc = fitz.open(str(file_path))
    except Exception as exc:
        raise IngestionError(
            f"Cannot open PDF: {exc}",
            code="PDF_OPEN_FAILED",
        ) from exc

    try:
        sample_pages = min(5, len(doc))
        if sample_pages == 0:
            raise IngestionError("PDF has no pages", code="PDF_EMPTY")

        total_chars = 0
        for page_index in range(sample_pages):
            total_chars += len(doc[page_index].get_text().strip())
    finally:
        doc.close()

    avg_chars = total_chars / sample_pages
    kind = DocumentKind.DIGITAL if avg_chars >= DIGITAL_TEXT_DENSITY_THRESHOLD else DocumentKind.SCANNED

    logger.info(
        "Document type detected",
        file=file_path.name,
        kind=kind.value,
        avg_chars_per_page=round(avg_chars, 1),
        threshold=DIGITAL_TEXT_DENSITY_THRESHOLD,
    )
    return kind


# ---------------------------------------------------------------------------
# Step 2a — Digital PDF extraction
# ---------------------------------------------------------------------------

def extract_digital_pdf(file_path: Path) -> tuple[list[PageText], list[ExtractionWarning]]:
    """
    Extract text from a digital (text-selectable) PDF using PyMuPDF.
    Falls back to pdfplumber for pages that yield very little text
    (e.g., pages with embedded tables).
    """
    warnings: list[ExtractionWarning] = []
    pages: list[PageText] = []

    try:
        doc = fitz.open(str(file_path))
    except Exception as exc:
        raise IngestionError(f"PyMuPDF open failed: {exc}", code="PDF_OPEN_FAILED") from exc

    plumber_doc = None
    try:
        try:
            plumber_doc = pdfplumber.open(str(file_path))
        except Exception:
            plumber_doc = None

        for page_index in range(len(doc)):
            page_num = page_index + 1
            fitz_page = doc[page_index]
            text = fitz_page.get_text().strip()

            # If PyMuPDF yields almost nothing, try pdfplumber (handles tables better)
            if len(text) < 30 and plumber_doc is not None:
                try:
                    plumber_page = plumber_doc.pages[page_index]
                    table_text = _extract_tables_from_plumber_page(plumber_page)
                    para_text  = plumber_page.extract_text() or ""
                    combined   = (para_text + "\n" + table_text).strip()
                    if len(combined) > len(text):
                        text = combined
                        logger.debug(
                            "Used pdfplumber for page",
                            page=page_num,
                            chars=len(text),
                        )
                except Exception as exc:
                    warnings.append(ExtractionWarning(
                        code="PLUMBER_PAGE_FAILED",
                        message=str(exc),
                        page=page_num,
                    ))

            if not text:
                warnings.append(ExtractionWarning(
                    code="EMPTY_PAGE",
                    message=f"Page {page_num} yielded no text",
                    page=page_num,
                ))

            pages.append(PageText(page_number=page_num, text=text, ocr_confidence=1.0))

    finally:
        doc.close()
        if plumber_doc:
            plumber_doc.close()

    return pages, warnings


def _extract_tables_from_plumber_page(page) -> str:
    """Extract all tables from a pdfplumber page as pipe-delimited text."""
    lines = []
    try:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                cleaned = [cell.strip() if cell else "" for cell in row]
                lines.append(" | ".join(cleaned))
    except Exception:
        pass
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 2b — Scanned PDF / Image extraction (OCR)
# ---------------------------------------------------------------------------

def extract_scanned_pdf(
    file_path: Path,
) -> tuple[list[PageText], list[ExtractionWarning]]:
    """
    Convert each PDF page to an image, preprocess with OpenCV,
    run Tesseract OCR, and collect per-page confidence scores.
    """
    warnings: list[ExtractionWarning] = []
    pages: list[PageText] = []

    # Determine page count without loading any images.
    try:
        _probe = fitz.open(str(file_path))
        page_count = len(_probe)
        _probe.close()
    except Exception as exc:
        raise IngestionError(
            f"Cannot read PDF page count: {exc}",
            code="PDF_OPEN_FAILED",
        ) from exc

    # Process one page at a time to avoid loading the entire document into RAM.
    # A 300 DPI A4 page ≈ 25 MB RGB; loading all at once for a 200-page document
    # would require ~5 GB.  Streaming keeps peak usage at ~75 MB (3 live frames).
    for page_num in range(1, page_count + 1):
        try:
            images = convert_from_path(
                str(file_path), dpi=300,
                first_page=page_num, last_page=page_num,
            )
            pil_img = images[0]
            del images  # release the list; pil_img holds the only remaining ref

            preprocessed = _preprocess_image_for_ocr(pil_img)
            del pil_img  # original no longer needed once preprocessed

            text, confidence = _run_tesseract(preprocessed, page_num)
            del preprocessed  # free after OCR

            pages.append(PageText(
                page_number=page_num,
                text=text,
                ocr_confidence=confidence,
            ))
            logger.debug(
                "OCR complete for page",
                page=page_num,
                confidence=round(confidence, 3),
                chars=len(text),
            )
        except IngestionError:
            raise
        except Exception as exc:
            warnings.append(ExtractionWarning(
                code="OCR_PAGE_FAILED",
                message=str(exc),
                page=page_num,
            ))
            pages.append(PageText(page_number=page_num, text="", ocr_confidence=0.0))

    return pages, warnings


def extract_image_file(
    file_path: Path,
) -> tuple[list[PageText], list[ExtractionWarning]]:
    """OCR a single image file (PNG, JPEG, TIFF, etc.)."""
    warnings: list[ExtractionWarning] = []
    try:
        pil_img = Image.open(str(file_path)).convert("RGB")
        preprocessed = _preprocess_image_for_ocr(pil_img)
        text, confidence = _run_tesseract(preprocessed, page_num=1)
        return [PageText(page_number=1, text=text, ocr_confidence=confidence)], warnings
    except Exception as exc:
        raise IngestionError(
            f"Image OCR failed: {exc}",
            code="IMAGE_OCR_FAILED",
        ) from exc


def _preprocess_image_for_ocr(pil_img: Image.Image) -> Image.Image:
    """
    OpenCV preprocessing pipeline:
    1. Convert to grayscale
    2. Deskew (correct tilt up to ±5°)
    3. Denoise
    4. Adaptive thresholding (binarize)

    Returns a PIL Image ready for Tesseract.
    """
    # PIL → OpenCV (BGR)
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # 1. Grayscale
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # 2. Deskew
    gray = _deskew(gray)

    # 3. Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    # 4. Adaptive threshold (binarize for cleaner OCR)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )

    # OpenCV → PIL
    return Image.fromarray(binary)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Correct small rotation angles in scanned pages."""
    try:
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) == 0:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) > 5:   # only correct if tilt > 5° to avoid distortion
            return gray
        h, w = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception:
        return gray   # deskew is best-effort


def _run_tesseract(pil_img: Image.Image, page_num: int) -> tuple[str, float]:
    """
    Run Tesseract OCR and return (text, avg_confidence).
    Confidence is the mean of per-word confidence scores (0.0–1.0).
    """
    try:
        data = pytesseract.image_to_data(
            pil_img,
            config=TESSERACT_CONFIG,
            output_type=pytesseract.Output.DICT,
            lang="eng+hin",
        )
    except Exception as exc:
        raise IngestionError(
            f"Tesseract failed on page {page_num}: {exc}",
            code="TESSERACT_FAILED",
        ) from exc

    words = []
    confidences = []

    for i, word in enumerate(data["text"]):
        conf = int(data["conf"][i])
        if conf == -1 or not word.strip():
            continue
        words.append(word)
        confidences.append(conf / 100.0)   # normalize to 0–1

    text = " ".join(words)
    avg_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0

    return text, avg_confidence


# ---------------------------------------------------------------------------
# Step 3 — Text cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """
    Normalize extracted text:
    - Fix encoding artifacts
    - Collapse excessive whitespace
    - Remove repeated noise lines
    - Remove empty lines
    """
    if not text:
        return ""

    # Fix common encoding artifacts
    text = text.encode("utf-8", errors="ignore").decode("utf-8")

    # Replace non-breaking spaces and other unicode whitespace
    text = re.sub(r"[\u00a0\u200b\u200c\u200d\ufeff]", " ", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove lines that are pure noise (only symbols, no alphanumeric content)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that are purely punctuation/symbols with no letters/digits
        if stripped and not re.search(r"[A-Za-z0-9\u0900-\u097F]", stripped):
            continue
        cleaned_lines.append(stripped)

    text = "\n".join(cleaned_lines)

    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple spaces into one
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


# ---------------------------------------------------------------------------
# Step 4 — Chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[str]:
    """
    Split text into chunks for RAG indexing.

    Strategy:
    1. Split on double-newlines (\n\n) → each paragraph = one chunk
    2. Paragraphs larger than chunk_size are split on single newlines
    3. Lines still larger than chunk_size are word-split with overlap
    4. Overlap tail is prepended to the next chunk for context continuity
    """
    if not text.strip():
        return []

    # Step 1: split on paragraph boundaries
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]

    # Step 2: for large paragraphs, split on single newlines
    lines: list[str] = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            lines.append(para)
        else:
            sub = [l.strip() for l in para.split("\n") if l.strip()]
            lines.extend(sub)

    # Step 3: word-split any line still exceeding chunk_size
    units: list[str] = []
    for line in lines:
        if len(line) <= chunk_size:
            units.append(line)
        else:
            words = line.split()
            part: list[str] = []
            part_size = 0
            for word in words:
                if part_size + len(word) + 1 > chunk_size and part:
                    units.append(" ".join(part))
                    carry = " ".join(part)[-overlap:]
                    part = carry.split() + [word] if carry.strip() else [word]
                    part_size = sum(len(w) + 1 for w in part)
                else:
                    part.append(word)
                    part_size += len(word) + 1
            if part:
                units.append(" ".join(part))

    if not units:
        return []

    # Step 4: each unit becomes its own chunk; prepend overlap tail from previous
    chunks: list[str] = []
    prev_tail = ""
    for unit in units:
        if prev_tail:
            chunk = (prev_tail + " " + unit).strip()
        else:
            chunk = unit
        chunks.append(chunk)
        prev_tail = unit[-overlap:] if len(unit) > overlap else unit

    return [c.strip() for c in chunks if c.strip()]


def _split_into_sentences(text: str) -> list[str]:
    """
    Simple sentence splitter using regex.
    Handles common Indian legal document patterns.
    """
    # Split on sentence-ending punctuation followed by whitespace + capital letter
    sentence_endings = re.compile(r"(?<=[.!?])\s+(?=[A-Z\u0900-\u097F])")
    sentences = sentence_endings.split(text)
    return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# Step 5 — OCR quality aggregation
# ---------------------------------------------------------------------------

def compute_ocr_quality(pages: list[PageText]) -> float:
    """
    Weighted average OCR confidence across all pages.
    Digital pages always contribute 1.0.
    Returns a score between 0.0 and 1.0.
    """
    if not pages:
        return 0.0
    total = sum(p.ocr_confidence for p in pages)
    return round(total / len(pages), 4)


# ---------------------------------------------------------------------------
# Custom Exception
# ---------------------------------------------------------------------------

class IngestionError(Exception):
    def __init__(self, message: str, code: str = "INGESTION_ERROR"):
        self.code = code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Main orchestration function
# ---------------------------------------------------------------------------

def process_document(
    file_path: str | Path,
    job_id: str | uuid.UUID,
    file_id: str | uuid.UUID,
    file_type: str,
) -> ExtractedDocument:
    """
    Main entry point for the ingestion pipeline.

    Orchestrates:
        detect type → extract text → clean → chunk → score → return

    Args:
        file_path:  Absolute path to the uploaded file.
        job_id:     UUID of the evaluation job.
        file_id:    UUID of the file record in the DB.
        file_type:  "tender" or "bidder_document".

    Returns:
        ExtractedDocument with all fields populated.

    Raises:
        IngestionError: If the file cannot be processed.
    """
    file_path = Path(file_path)
    job_id    = uuid.UUID(str(job_id))
    file_id   = uuid.UUID(str(file_id))

    log = logger.bind(
        file=file_path.name,
        job_id=str(job_id),
        file_id=str(file_id),
        file_type=file_type,
    )
    log.info("Ingestion started")

    if not file_path.exists():
        raise IngestionError(
            f"File not found: {file_path}",
            code="FILE_NOT_FOUND",
        )

    # ── Step 1: Detect document kind ─────────────────────────────────────
    kind = detect_document_kind(file_path)

    # ── Step 2: Extract text ─────────────────────────────────────────────
    warnings: list[ExtractionWarning] = []

    if kind == DocumentKind.DIGITAL:
        log.info("Using digital PDF extraction (PyMuPDF + pdfplumber)")
        pages, extraction_warnings = extract_digital_pdf(file_path)
        warnings.extend(extraction_warnings)

    elif kind == DocumentKind.SCANNED:
        log.info("Using OCR extraction (pdf2image + OpenCV + Tesseract)")
        pages, extraction_warnings = extract_scanned_pdf(file_path)
        warnings.extend(extraction_warnings)

    elif kind == DocumentKind.IMAGE:
        log.info("Using image OCR extraction (OpenCV + Tesseract)")
        pages, extraction_warnings = extract_image_file(file_path)
        warnings.extend(extraction_warnings)

    else:
        raise IngestionError(f"Unknown document kind: {kind}", code="UNKNOWN_KIND")

    if not pages:
        raise IngestionError("No pages extracted from document", code="NO_PAGES")

    # ── Step 3: Clean text ───────────────────────────────────────────────
    page_texts: dict[int, str] = {}
    for page in pages:
        page.text = clean_text(page.text)
        page_texts[page.page_number] = page.text

    raw_text = "\n\n".join(
        pt.text for pt in sorted(pages, key=lambda p: p.page_number)
        if pt.text
    )

    if not raw_text.strip():
        warnings.append(ExtractionWarning(
            code="EMPTY_DOCUMENT",
            message="All pages produced empty text after cleaning",
        ))
        log.warning("Document produced empty text after extraction")

    # ── Step 4: Chunk ────────────────────────────────────────────────────
    # CHUNK_SIZE / CHUNK_OVERLAP are in characters (settings uses same unit).
    # Tune them via .env: CHUNK_SIZE=2400, CHUNK_OVERLAP=200.
    from app.core.settings import settings as _settings
    chunks = chunk_text(
        raw_text,
        chunk_size=_settings.CHUNK_SIZE,
        overlap=_settings.CHUNK_OVERLAP,
    )

    # ── Step 5: OCR quality score ────────────────────────────────────────
    ocr_quality = compute_ocr_quality(pages)

    # ── Step 6: Log summary ──────────────────────────────────────────────
    log.info(
        "Ingestion complete",
        kind=kind.value,
        page_count=len(pages),
        char_count=len(raw_text),
        chunk_count=len(chunks),
        ocr_quality_score=ocr_quality,
        warning_count=len(warnings),
    )

    return ExtractedDocument(
        file_id=file_id,
        job_id=job_id,
        file_type=file_type,
        document_kind=kind,
        raw_text=raw_text,
        page_texts=page_texts,
        chunks=chunks,
        ocr_quality_score=ocr_quality,
        page_count=len(pages),
        char_count=len(raw_text),
        chunk_count=len(chunks),
        warnings=warnings,
    )
