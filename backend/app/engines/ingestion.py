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
    """
    Per-page extraction record.

    `ocr_confidence` is the core Tesseract word-confidence mean (0..1), set
    to 1.0 for digital pages that did not go through OCR. The remaining
    fields are additional signals consumed by `compute_ocr_quality()` so
    the final OCR-quality score reflects REAL document characteristics
    (blur, skew, text density, empty pages) rather than just the engine's
    word-level confidence.
    """
    page_number: int        # 1-indexed
    text: str
    ocr_confidence: float = 1.0   # 1.0 for digital; Tesseract avg for scanned
    # Normalized chars per page, clipped to [0, 1]. 1.0 ≈ a well-filled
    # text page (~1500 chars). 0.0 ≈ a fully empty page.
    text_density: float = 1.0
    # Laplacian-variance sharpness proxy, normalized to [0, 1]. 1.0 = crisp,
    # 0.0 = heavily blurred. Always 1.0 for digital pages (no raster to blur).
    sharpness: float = 1.0
    # Absolute deskew angle in degrees — how much rotation was needed to
    # straighten the page. 0.0 for digital; up to ~10° on bad scans.
    skew_abs_deg: float = 0.0
    # True if the page produced no usable text after cleaning.
    is_empty: bool = False


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
    ocr_quality_score: float                     # 0.0 – 1.0  (composite)
    page_count:       int
    char_count:       int
    chunk_count:      int
    warnings:         list[ExtractionWarning] = field(default_factory=list)
    # Auditable per-signal breakdown that produced `ocr_quality_score`.
    # Populated by `compute_ocr_quality()` via `ocr_quality_breakdown()`;
    # written into the INGESTION_DONE audit log so operators can see WHY
    # a particular document landed at, e.g., 73%.
    ocr_quality_breakdown: dict = field(default_factory=dict)
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

            # Digital pages: OCR wasn't run, so ocr_confidence / sharpness /
            # skew stay at 1.0 / 1.0 / 0.0. The only real signal we have is
            # text density (empty pages and light pages still pull quality
            # down appropriately even for a supposedly-digital PDF).
            pages.append(PageText(
                page_number=page_num,
                text=text,
                ocr_confidence=1.0,
                text_density=_page_text_density(text),
                sharpness=1.0,
                skew_abs_deg=0.0,
                is_empty=not text,
            ))

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

            preprocessed, sharpness, skew_abs = _preprocess_image_for_ocr(pil_img)
            del pil_img  # original no longer needed once preprocessed

            text, confidence = _run_tesseract(preprocessed, page_num)
            del preprocessed  # free after OCR

            pages.append(PageText(
                page_number=page_num,
                text=text,
                ocr_confidence=confidence,
                text_density=_page_text_density(text),
                sharpness=sharpness,
                skew_abs_deg=skew_abs,
                is_empty=not text.strip(),
            ))
            logger.debug(
                "OCR complete for page",
                page=page_num,
                confidence=round(confidence, 3),
                chars=len(text),
                sharpness=sharpness,
                skew_abs_deg=skew_abs,
            )
        except IngestionError:
            raise
        except Exception as exc:
            warnings.append(ExtractionWarning(
                code="OCR_PAGE_FAILED",
                message=str(exc),
                page=page_num,
            ))
            # Failed-page record: zero confidence, zero density, flagged
            # empty — pulls the aggregate OCR quality down honestly rather
            # than silently vanishing from the average.
            pages.append(PageText(
                page_number=page_num, text="",
                ocr_confidence=0.0,
                text_density=0.0,
                sharpness=0.0,
                skew_abs_deg=0.0,
                is_empty=True,
            ))

    return pages, warnings


def extract_image_file(
    file_path: Path,
) -> tuple[list[PageText], list[ExtractionWarning]]:
    """OCR a single image file (PNG, JPEG, TIFF, etc.)."""
    warnings: list[ExtractionWarning] = []
    try:
        pil_img = Image.open(str(file_path)).convert("RGB")
        preprocessed, sharpness, skew_abs = _preprocess_image_for_ocr(pil_img)
        text, confidence = _run_tesseract(preprocessed, page_num=1)
        return [PageText(
            page_number=1, text=text,
            ocr_confidence=confidence,
            text_density=_page_text_density(text),
            sharpness=sharpness,
            skew_abs_deg=skew_abs,
            is_empty=not text.strip(),
        )], warnings
    except Exception as exc:
        raise IngestionError(
            f"Image OCR failed: {exc}",
            code="IMAGE_OCR_FAILED",
        ) from exc


def _preprocess_image_for_ocr(pil_img: Image.Image) -> tuple[Image.Image, float, float]:
    """
    OpenCV preprocessing pipeline:
      1. Convert to grayscale
      2. Measure sharpness (Laplacian variance — BEFORE denoising so the
         value reflects the true scan quality, not the cleaned image)
      3. Deskew (correct tilt up to ±5°)
      4. Denoise
      5. Adaptive thresholding (binarize)

    Returns:
        (preprocessed_pil_image, sharpness_norm, skew_abs_deg)

        `sharpness_norm`  ∈ [0, 1] — 1.0 = crisp scan, 0.0 = heavily blurred.
                           Derived from Laplacian variance / 800; clipped.
                           (800 is the empirical knee where Tesseract starts
                           losing recall on 300-DPI document scans.)
        `skew_abs_deg`    ≥ 0   — absolute skew angle detected before
                           rotation; used to penalize heavily-tilted pages.
    """
    # PIL → OpenCV (BGR)
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # 1. Grayscale
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # 2. Sharpness BEFORE we blur/denoise — so we measure the scan, not
    #    our own cleanup. Laplacian variance is a standard blur proxy.
    try:
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception:
        lap_var = 800.0            # benign fallback (≈ clean-scan knee)
    sharpness_norm = max(0.0, min(1.0, lap_var / 800.0))

    # 3. Deskew (also reports the magnitude it detected)
    gray, skew_abs = _deskew(gray)

    # 4. Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    # 5. Adaptive threshold (binarize for cleaner OCR)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )

    # OpenCV → PIL
    return Image.fromarray(binary), round(sharpness_norm, 4), round(skew_abs, 4)


def _deskew(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Correct small rotation angles in scanned pages.

    Returns:
        (deskewed_gray, abs_angle_detected_degrees)

    If the detected tilt exceeds ±5° we leave the page untouched (warping
    more than that introduces worse artifacts than it fixes), but the
    detected angle is still reported so `compute_ocr_quality` can penalize
    it.  `0.0` means no measurable skew.
    """
    try:
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) == 0:
            return gray, 0.0
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        abs_angle = abs(float(angle))
        if abs_angle > 5:
            # Skip rotation but still report — a 10° tilt is a real quality issue.
            return gray, abs_angle
        h, w = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated, abs_angle
    except Exception:
        return gray, 0.0   # deskew is best-effort; absence of signal → 0


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
#
# Production-grade, deterministic, multi-signal document-quality score in
# [0, 1]. Two branches — digital PDFs and scanned PDFs — because they have
# completely different signal profiles (no raster → no blur/skew to
# measure; conversely a scan's text density follows from OCR recall rather
# than the source PDF layout).
#
# All inputs come from `PageText` fields already populated during
# extraction (see `_preprocess_image_for_ocr`, `_run_tesseract`,
# `extract_digital_pdf`, `extract_scanned_pdf`). No external calls, no DB,
# no randomness — same PDF → same score across runs.
#
# Expected realistic ranges (matches user-facing spec):
#   clean digital PDFs      → 0.95 – 1.00
#   mixed digital (some
#     empty/low-density)    → 0.85 – 0.95
#   high-quality scans      → 0.80 – 0.95
#   noisy / skewed scans    → 0.55 – 0.80
#   blurry / low-text scans → 0.30 – 0.55
#   unreadable              → 0.00 – 0.30
#
# The formula is intentionally NOT a simple Tesseract average (the old
# behaviour that produced suspiciously-identical scores).
# ---------------------------------------------------------------------------

# Normalization knees — chosen empirically on Indian-English tender PDFs at
# 300 DPI. Changing these values moves the entire distribution, so they
# live in one place.
_TEXT_DENSITY_FULL_CHARS   = 1500    # chars/page considered "well filled"
_SHARPNESS_LAP_VAR_KNEE    = 800.0   # Laplacian variance knee (see preprocess)
_SKEW_SATURATION_DEG       = 5.0     # > this many degrees = fully penalized


def _page_text_density(text: str) -> float:
    """
    Normalize raw char count to [0, 1] using _TEXT_DENSITY_FULL_CHARS as
    the saturation point. An empty page = 0.0; a dense text page = 1.0.
    Pure function of the cleaned text — deterministic across runs.
    """
    if not text:
        return 0.0
    chars = len(text.strip())
    return max(0.0, min(1.0, chars / float(_TEXT_DENSITY_FULL_CHARS)))


def compute_ocr_quality(
    pages: list[PageText],
    kind: "DocumentKind | None" = None,
) -> float:
    """
    Composite OCR/document-quality score in [0, 1].

    `kind` (optional) allows the caller to force the digital/scanned
    branch; when omitted, the branch is inferred from whether any page
    carries a sub-1.0 Tesseract confidence (the tell-tale sign that OCR
    actually ran on that page).

    Digital branch (no OCR run):
        quality = 1.00
                - 0.25 × empty_page_ratio
                - 0.15 × low_density_ratio     (pages < 100 chars)
                - 0.10 × (1 − mean_text_density)

    Scanned branch (OCR run):
        quality = 0.50 × tesseract_mean_conf
                + 0.15 × mean_sharpness
                + 0.15 × mean_text_density
                + 0.10 × (1 − mean_skew / 5.0)   clipped
                + 0.05 × (1 − empty_ratio)
                + 0.05 × coverage_bonus          (fraction of pages with
                                                   any recognised words)
    """
    if not pages:
        return 0.0

    # Clamp per-page signals defensively — callers could pass anything.
    def _clip01(x: float) -> float:
        return max(0.0, min(1.0, float(x)))

    n = len(pages)
    ran_ocr = any(p.ocr_confidence < 1.0 for p in pages)

    # Infer branch if not forced by the caller. Digital pages always have
    # ocr_confidence == 1.0; if even one page shows a lower value, the
    # pipeline ran OCR and we're in the scanned branch.
    is_scanned = (
        ran_ocr
        if kind is None
        else (kind is not None and kind.value != "digital")
    )

    empty_ratio         = sum(1 for p in pages if p.is_empty) / n
    low_density_ratio   = sum(1 for p in pages if len(p.text.strip()) < 100) / n
    mean_text_density   = sum(_clip01(p.text_density) for p in pages) / n
    mean_sharpness      = sum(_clip01(p.sharpness) for p in pages) / n
    mean_skew           = sum(max(0.0, float(p.skew_abs_deg)) for p in pages) / n
    coverage            = sum(1 for p in pages if p.text.strip()) / n

    if not is_scanned:
        quality = (
            1.00
            - 0.25 * empty_ratio
            - 0.15 * low_density_ratio
            - 0.10 * (1.0 - mean_text_density)
        )
    else:
        mean_conf    = sum(_clip01(p.ocr_confidence) for p in pages) / n
        skew_penalty = _clip01(mean_skew / _SKEW_SATURATION_DEG)
        quality = (
            0.50 * mean_conf
            + 0.15 * mean_sharpness
            + 0.15 * mean_text_density
            + 0.10 * (1.0 - skew_penalty)
            + 0.05 * (1.0 - empty_ratio)
            + 0.05 * coverage
        )

    return round(max(0.0, min(1.0, quality)), 4)


def ocr_quality_breakdown(pages: list[PageText]) -> dict:
    """
    Introspectable breakdown of the per-signal inputs that fed into
    `compute_ocr_quality`. Intended for audit logs / verifiers — NOT on the
    hot path. Returns per-signal means + a copy of each knee constant so
    downstream consumers can reproduce the formula.
    """
    if not pages:
        return {"n_pages": 0}

    def _clip01(x: float) -> float:
        return max(0.0, min(1.0, float(x)))

    n = len(pages)
    return {
        "n_pages":            n,
        "branch":             "scanned" if any(p.ocr_confidence < 1.0 for p in pages) else "digital",
        "mean_ocr_confidence":     round(sum(_clip01(p.ocr_confidence) for p in pages) / n, 4),
        "mean_text_density":       round(sum(_clip01(p.text_density)   for p in pages) / n, 4),
        "mean_sharpness":          round(sum(_clip01(p.sharpness)      for p in pages) / n, 4),
        "mean_skew_abs_deg":       round(sum(max(0.0, float(p.skew_abs_deg)) for p in pages) / n, 4),
        "empty_page_ratio":        round(sum(1 for p in pages if p.is_empty) / n, 4),
        "low_density_page_ratio":  round(sum(1 for p in pages if len(p.text.strip()) < 100) / n, 4),
        "coverage":                round(sum(1 for p in pages if p.text.strip()) / n, 4),
        "knees": {
            "text_density_full_chars": _TEXT_DENSITY_FULL_CHARS,
            "sharpness_lap_var_knee":  _SHARPNESS_LAP_VAR_KNEE,
            "skew_saturation_deg":     _SKEW_SATURATION_DEG,
        },
    }


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
    # Recompute text-derived signals AFTER cleaning so `compute_ocr_quality`
    # operates on what we actually retain (cleaning can drop noise lines,
    # which is exactly what should affect the quality score).
    page_texts: dict[int, str] = {}
    for page in pages:
        page.text = clean_text(page.text)
        page.text_density = _page_text_density(page.text)
        page.is_empty     = not page.text.strip()
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
    # Force the digital/scanned branch from the detected kind so a digital
    # PDF that happens to have one OCR-confidence-< 1.0 page (extreme edge
    # case from a malformed extractor) cannot accidentally flip into the
    # scanned branch.
    ocr_quality = compute_ocr_quality(pages, kind=kind)
    breakdown   = ocr_quality_breakdown(pages)

    # ── Step 6: Log summary ──────────────────────────────────────────────
    log.info(
        "Ingestion complete",
        kind=kind.value,
        page_count=len(pages),
        char_count=len(raw_text),
        chunk_count=len(chunks),
        ocr_quality_score=ocr_quality,
        ocr_breakdown=breakdown,
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
        ocr_quality_breakdown=breakdown,
        page_count=len(pages),
        char_count=len(raw_text),
        chunk_count=len(chunks),
        warnings=warnings,
    )
