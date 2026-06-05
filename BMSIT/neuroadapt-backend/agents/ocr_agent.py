"""
OCR Agent: Extract text from PDFs or images.

Primary strategy: PyMuPDF (fitz) for digital PDFs with text layers.
Fallback strategy: pytesseract + pdf2image for scanned PDFs.

No inter-agent imports. All exceptions caught and logged locally.

FIXES:
- fitz.open() now handles both bytes and Path correctly; doc.close() moved AFTER
  the len(doc) log so we don't call len() on a closed document (RuntimeError).
- Tesseract image-from-bytes now wraps bytes in BytesIO (PIL requires file-like,
  not raw bytes).
- Added _log_extracted_preview() helper that prints first 500 chars of extracted
  text so you can see exactly what came out of each strategy.
"""

import io
import logging
import re
import unicodedata
from pathlib import Path
from typing import Union

from models import PipelineState

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _log_extracted_preview(strategy: str, text: str) -> None:
    """Log the first 500 characters of extracted text so you can verify it."""
    preview = text.strip()[:500].replace("\n", "↵")  # make newlines visible
    char_count = len(text.strip())
    logger.info(
        f"[AGENT:ocr] ── EXTRACTION PREVIEW ({strategy}) ──\n"
        f"  Total chars (raw): {char_count}\n"
        f"  Preview (first 500 chars, ↵=newline):\n"
        f"  {preview}\n"
        f"[AGENT:ocr] ── END PREVIEW ──"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 1: PyMuPDF
# ─────────────────────────────────────────────────────────────────────────────

def _extract_text_pdfplumber(source: Union[str, bytes, Path]) -> str:
    """
    Extract text from PDF using pdfplumber (primary strategy).
    
    pdfplumber is more reliable for text extraction from both digital and scanned PDFs.
    Handles both file paths and raw bytes.
    Returns concatenated page text, or empty string on any failure.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning("[AGENT:ocr] pdfplumber not installed — skipping")
        return ""

    try:
        if isinstance(source, bytes):
            import io
            logger.debug(f"[AGENT:ocr] pdfplumber: opening from bytes ({len(source):,} bytes)")
            pdf_file = io.BytesIO(source)
            pdf = pdfplumber.open(pdf_file)
        else:
            path = Path(source)
            logger.debug(f"[AGENT:ocr] pdfplumber: opening from path {path}")
            pdf = pdfplumber.open(str(path))

        page_count = len(pdf.pages)
        logger.info(f"[AGENT:ocr] pdfplumber: opened PDF — {page_count} page(s)")
        
        text = ""
        for i, page in enumerate(pdf.pages):
            try:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
                logger.debug(f"[AGENT:ocr] pdfplumber: extracted {len(page_text)} chars from page {i+1}")
            except Exception as e:
                logger.warning(f"[AGENT:ocr] pdfplumber: failed to extract page {i+1}: {str(e)}")
                continue
        
        pdf.close()
        _log_extracted_preview("pdfplumber", text)
        extracted = text.strip()
        if _looks_like_pdf_metadata(extracted):
            logger.warning("[AGENT:ocr] pdfplumber result appears to be PDF metadata only; ignoring")
            return ""
        return extracted
        
    except Exception as e:
        logger.error(f"[AGENT:ocr] pdfplumber extraction failed: {str(e)}")
        return ""


def _looks_like_pdf_metadata(text: str) -> bool:
    trimmed = text.strip()
    if not trimmed:
        return False

    pdf_markers = [
        r"\/(Author|Creator|Producer|CreationDate|ModDate|Title|Pages|Font|Subtype|Filter|Length|Resources|MediaBox|Contents|Catalog)\b",
        r"\bobj\b",
        r"\bendobj\b",
        r"<<|>>",
        r"\/Type\s*\/Page",
        r"\/Filter\b"
    ]
    marker_count = sum(1 for pattern in pdf_markers if re.search(pattern, trimmed))
    if marker_count >= 3:
        return True

    slash_lines = len(re.findall(r"^\s*\/\w+", trimmed, re.MULTILINE))
    if slash_lines >= 3:
        return True

    word_count = len(trimmed.split())
    pdf_keyword_count = len(re.findall(r"\b(?:obj|endobj|stream|endstream|xref|trailer|<<|>>|\/Type|\/Length|\/Filter|\/Font)\b", trimmed))
    return pdf_keyword_count > max(3, int(word_count * 0.1))


def _extract_text_pymupdf(source: Union[str, bytes, Path]) -> str:
    """
    Extract text from PDF using PyMuPDF (fitz) - fallback strategy.

    Fallback path. Handles both file paths and raw bytes.
    Returns concatenated page text, or empty string on any failure.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("[AGENT:ocr] PyMuPDF (fitz) not installed — skipping")
        return ""

    doc = None
    try:
        if isinstance(source, bytes):
            logger.debug(f"[AGENT:ocr] PyMuPDF: opening from bytes ({len(source):,} bytes)")
            doc = fitz.open(stream=source, filetype="pdf")
        else:
            path = Path(source)
            logger.debug(f"[AGENT:ocr] PyMuPDF: opening from path {path}")
            doc = fitz.open(str(path))  # fitz wants a str, not Path on some versions

        page_count = len(doc)  # do this BEFORE close
        logger.info(f"[AGENT:ocr] PyMuPDF: opened PDF — {page_count} page(s)")

        pages_text: list[str] = []
        for page_num in range(page_count):
            try:
                page = doc[page_num]
                text = page.get_text()
                pages_text.append(text)
                logger.debug(
                    f"[AGENT:ocr] PyMuPDF: page {page_num + 1}/{page_count} "
                    f"→ {len(text):,} chars"
                )
            except Exception as page_err:
                logger.warning(
                    f"[AGENT:ocr] PyMuPDF: failed on page {page_num + 1}: {page_err}"
                )
                pages_text.append("")

        result = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
        logger.info(
            f"[AGENT:ocr] PyMuPDF: extraction complete — "
            f"{page_count} pages, {len(result):,} total chars"
        )
        _log_extracted_preview("PyMuPDF", result)
        if _looks_like_pdf_metadata(result):
            logger.warning("[AGENT:ocr] PyMuPDF result appears to be PDF metadata only; ignoring")
            return ""
        return result

    except Exception as e:
        logger.error(f"[AGENT:ocr] PyMuPDF: extraction failed — {e}", exc_info=True)
        return ""
    finally:
        # Always close, but only AFTER we're done using the doc object
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Strategy 2: Tesseract OCR (fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_text_tesseract(source: Union[str, bytes, Path]) -> str:
    """
    Extract text from image or scanned PDF using Tesseract OCR.

    Fallback path. Triggered when PyMuPDF produces < 100 chars, or for image
    source_type inputs.

    BUG FIXED: PIL Image.open() requires a file-like object, not raw bytes.
    Raw bytes are now wrapped in io.BytesIO() before passing to Image.open().
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path, convert_from_bytes
        from PIL import Image
    except ImportError as e:
        logger.warning(f"[AGENT:ocr] Tesseract deps not installed ({e}) — skipping")
        return ""

    images: list = []

    try:
        if isinstance(source, bytes):
            logger.debug(f"[AGENT:ocr] Tesseract: received bytes ({len(source):,} bytes)")

            if source[:4] == b"%PDF":
                logger.info("[AGENT:ocr] Tesseract: bytes are a PDF — rasterising at 300 DPI")
                try:
                    images = convert_from_bytes(source, dpi=300)
                    logger.info(f"[AGENT:ocr] Tesseract: PDF → {len(images)} image(s)")
                except Exception as pdf_err:
                    logger.warning(
                        f"[AGENT:ocr] Tesseract: pdf2image failed ({pdf_err}), "
                        f"trying as raw image"
                    )
                    try:
                        # FIX: wrap bytes in BytesIO
                        images = [Image.open(io.BytesIO(source))]
                        logger.info("[AGENT:ocr] Tesseract: loaded bytes as image")
                    except Exception as img_err:
                        logger.error(f"[AGENT:ocr] Tesseract: image load also failed — {img_err}")
                        return ""
            else:
                logger.info("[AGENT:ocr] Tesseract: bytes look like image — loading directly")
                try:
                    # FIX: wrap bytes in BytesIO
                    images = [Image.open(io.BytesIO(source))]
                    logger.info("[AGENT:ocr] Tesseract: loaded image from bytes")
                except Exception as img_err:
                    logger.error(f"[AGENT:ocr] Tesseract: image load failed — {img_err}")
                    return ""

        else:
            path = Path(source)
            logger.debug(f"[AGENT:ocr] Tesseract: processing file path {path}")
            if path.suffix.lower() == ".pdf":
                logger.info("[AGENT:ocr] Tesseract: file is PDF — rasterising at 300 DPI")
                images = convert_from_path(str(path), dpi=300)
                logger.info(f"[AGENT:ocr] Tesseract: PDF → {len(images)} image(s)")
            else:
                logger.info(f"[AGENT:ocr] Tesseract: file is image ({path.suffix})")
                images = [Image.open(path)]

        if not images:
            logger.warning("[AGENT:ocr] Tesseract: no images to OCR")
            return ""

        logger.info(f"[AGENT:ocr] Tesseract: running OCR on {len(images)} image(s)")
        pages_text: list[str] = []
        for i, img in enumerate(images):
            try:
                text = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
                pages_text.append(text)
                logger.debug(
                    f"[AGENT:ocr] Tesseract: image {i + 1}/{len(images)} "
                    f"→ {len(text):,} chars"
                )
            except Exception as ocr_err:
                logger.warning(
                    f"[AGENT:ocr] Tesseract: OCR failed on image {i + 1}: {ocr_err}"
                )
                pages_text.append("")

        result = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
        logger.info(
            f"[AGENT:ocr] Tesseract: complete — {len(images)} image(s), "
            f"{len(result):,} total chars"
        )
        _log_extracted_preview("Tesseract", result)
        return result

    except Exception as e:
        logger.error(f"[AGENT:ocr] Tesseract: extraction failed — {e}", exc_info=True)
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Text normalisation
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    """
    Post-extraction cleanup:
      - Remove null bytes
      - Remove non-printable characters (keep \\n and \\t)
      - Normalise unicode to NFKC
      - Collapse 3+ consecutive newlines to 2
    """
    if not text:
        return ""

    text = text.replace("\x00", "")
    text = "".join(c for c in text if c in "\n\t" or c.isprintable())
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Agent entry point
# ─────────────────────────────────────────────────────────────────────────────

def run(state: PipelineState, source: Union[str, bytes], source_type: str) -> PipelineState:
    """
    Main OCR agent entry point.

    Args:
        state:       Shared pipeline state.
        source:      File path (str/Path) or raw file bytes.
        source_type: One of "pdf", "image", or "text".

    Returns:
        Updated PipelineState with raw_text populated.
        On total failure, raw_text is empty and state.degraded is True.
    """
    logger.info(
        f"[AGENT:ocr] ═══ START ═══ "
        f"source_type={source_type!r}, "
        f"input_type={type(source).__name__}, "
        f"size={'%d bytes' % len(source) if isinstance(source, bytes) else str(source)}"
    )

    raw_text = ""

    # ── Direct text input ────────────────────────────────────────────────────
    if source_type == "text":
        if isinstance(source, bytes):
            raw_text = source.decode("utf-8", errors="ignore")
        else:
            raw_text = str(source)
        logger.info(f"[AGENT:ocr] Direct text input: {len(raw_text):,} chars")
        _log_extracted_preview("direct-text", raw_text)

    # ── PDF input ─────────────────────────────────────────────────────────────
    elif source_type == "pdf":
        logger.info("[AGENT:ocr] Strategy 1: pdfplumber (primary)")
        raw_text = _extract_text_pdfplumber(source)
        logger.info(
            f"[AGENT:ocr] pdfplumber result: {len(raw_text.strip()):,} chars "
            f"(threshold=100)"
        )

        if len(raw_text.strip()) < 100:
            logger.warning(
                "[AGENT:ocr] pdfplumber returned < 100 chars — "
                "trying PyMuPDF as fallback."
            )
            pymupdf_text = _extract_text_pymupdf(source)
            logger.info(
                f"[AGENT:ocr] PyMuPDF fallback result: {len(pymupdf_text.strip()):,} chars"
            )
            if pymupdf_text.strip() and len(pymupdf_text.strip()) > len(raw_text.strip()):
                raw_text = pymupdf_text
        
        if len(raw_text.strip()) < 100:
            logger.warning(
                "[AGENT:ocr] Text extraction < 100 chars — "
                "likely scanned PDF. Falling back to Tesseract."
            )
            state.agent_statuses["ocr"] = "degraded"
            tesseract_text = _extract_text_tesseract(source)
            logger.info(
                f"[AGENT:ocr] Tesseract result: {len(tesseract_text.strip()):,} chars"
            )
            if tesseract_text.strip():
                raw_text = tesseract_text
            else:
                logger.error(
                    "[AGENT:ocr] All strategies (pdfplumber, PyMuPDF, Tesseract) returned empty text"
                )

    # ── Image input ───────────────────────────────────────────────────────────
    elif source_type == "image":
        logger.info("[AGENT:ocr] Strategy: Tesseract (image input)")
        raw_text = _extract_text_tesseract(source)
        logger.info(f"[AGENT:ocr] Tesseract result: {len(raw_text.strip()):,} chars")

    else:
        logger.warning(f"[AGENT:ocr] Unknown source_type={source_type!r} — no extraction attempted")

    # ── Final status ──────────────────────────────────────────────────────────
    if not raw_text.strip():
        logger.error("[AGENT:ocr] FAILED — no text produced by any strategy")
        state.degraded = True
        state.errors.append("ocr: No text could be extracted from the source")
        state.agent_statuses["ocr"] = "failed"
    else:
        raw_text = _normalize_text(raw_text)
        logger.info(
            f"[AGENT:ocr] ═══ COMPLETE ═══ "
            f"{len(raw_text):,} chars after normalisation "
            f"(degraded={state.degraded})"
        )
        if state.agent_statuses.get("ocr") != "degraded":
            state.agent_statuses["ocr"] = "ok"

    state.raw_text = raw_text
    return state