"""
ocr_module.py — Tesseract OCR wrapper for VeriNews
Extracts text from uploaded screenshot images.

Engine: pytesseract (Tesseract 5) — ~3-5 s per image on CPU.
Fallback: EasyOCR if Tesseract binary is not found.

Performance notes:
  - Images are pre-processed (resize to max 1200px, grayscale, auto-invert
    dark backgrounds) before Tesseract runs for best accuracy.
  - No background warmup needed — Tesseract is a native binary, not PyTorch.
"""
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
MAX_SIDE_PX   = 1200    # resize so longest side ≤ this (Tesseract handles larger
                        # images well, so we can be more generous than EasyOCR)
AUTO_INVERT   = True    # flip dark-background images to dark-text-on-white

# Tesseract config: page segmentation mode 3 (fully automatic),
# output as plain text, English language
TESS_CONFIG   = "--psm 3 -l eng"

# ── Compatibility flags (for the /ocr-status endpoint) ────────────────────────
_reader_ready = True    # Tesseract is always "ready" — no model warmup needed
_reader       = True    # truthy sentinel so existing checks pass


def warmup():
    """No-op: Tesseract needs no warmup. Kept for API compatibility."""
    pass


# ── Image pre-processing ──────────────────────────────────────────────────────

def _preprocess_image(image_path: str) -> str:
    """
    Prepare image for Tesseract:
      1. Resize so longest side ≤ MAX_SIDE_PX
      2. Convert to grayscale
      3. Auto-invert dark-background images (white-on-black → black-on-white)

    Returns path to a temp preprocessed file, or original path on failure.
    """
    try:
        from PIL import Image, ImageOps

        img     = Image.open(image_path).convert("RGB")
        w, h    = img.size
        longest = max(w, h)

        if longest > MAX_SIDE_PX:
            scale = MAX_SIDE_PX / longest
            img   = img.resize((max(1, int(w * scale)),
                                max(1, int(h * scale))), Image.LANCZOS)
            logger.info(f"[OCR] Resized {w}×{h} → {img.size}")

        img = img.convert("L")  # grayscale

        if AUTO_INVERT:
            pixels = list(img.getdata())
            if sum(pixels) / len(pixels) < 127:   # dark background
                img = ImageOps.invert(img)
                logger.info("[OCR] Dark background detected — inverted.")

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tmp.name, "PNG")
        tmp.close()
        return tmp.name

    except Exception:
        logger.warning("[OCR] Pre-processing failed; using original image.")
        return image_path


# ── Primary: Tesseract ────────────────────────────────────────────────────────

def _extract_with_tesseract(image_path: str) -> dict:
    """Run Tesseract OCR and return structured result."""
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

        # image_to_data gives per-word confidence scores
        data = pytesseract.image_to_data(
            image_path,
            config=TESS_CONFIG,
            output_type=pytesseract.Output.DICT
        )

        words       = []
        confidences = []
        for i, word in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if conf > 0 and word.strip():   # conf == -1 means non-text block
                words.append(word.strip())
                confidences.append(conf / 100.0)   # normalise 0-100 → 0-1

        if not words:
            return {"extracted_text": "", "confidence_score": 0.0,
                    "success": False, "error": "Tesseract returned no text."}

        avg_conf = sum(confidences) / len(confidences)
        extracted = " ".join(words)
        logger.info(f"[OCR] Tesseract: {len(words)} words, avg conf {avg_conf:.2f}")

        return {
            "extracted_text":   extracted,
            "confidence_score": round(avg_conf, 4),
            "success":          True,
            "error":            None,
        }

    except Exception as e:
        logger.warning(f"[OCR] Tesseract failed: {e}")
        return {"extracted_text": "", "confidence_score": 0.0,
                "success": False, "error": str(e)}


# ── Fallback: EasyOCR ─────────────────────────────────────────────────────────

def _extract_with_easyocr(image_path: str) -> dict:
    """EasyOCR fallback if Tesseract is unavailable."""
    try:
        import easyocr
        logger.info("[OCR] Falling back to EasyOCR.")
        reader  = easyocr.Reader(["en"], gpu=False, verbose=False)
        results = reader.readtext(image_path, detail=1)
        if not results:
            return {"extracted_text": "", "confidence_score": 0.0,
                    "success": False, "error": "EasyOCR returned no text."}
        texts  = [r[1] for r in results]
        confs  = [r[2] for r in results]
        return {
            "extracted_text":   " ".join(texts).strip(),
            "confidence_score": round(sum(confs) / len(confs), 4),
            "success":          True,
            "error":            None,
        }
    except Exception as e:
        return {"extracted_text": "", "confidence_score": 0.0,
                "success": False, "error": str(e)}


# ── Public API ────────────────────────────────────────────────────────────────

def extract_text(image_path: str) -> dict:
    """
    Extract text from an image file using Tesseract (fast) with EasyOCR fallback.

    Returns:
        {
            "extracted_text":   str,
            "confidence_score": float,   # 0.0 – 1.0
            "success":          bool,
            "error":            str | None
        }
    """
    if not os.path.exists(image_path):
        return {"extracted_text": "", "confidence_score": 0.0,
                "success": False, "error": f"File not found: {image_path}"}

    processed_path = image_path
    try:
        processed_path = _preprocess_image(image_path)

        # Try Tesseract first
        if os.path.exists(TESSERACT_CMD):
            result = _extract_with_tesseract(processed_path)
        else:
            logger.warning("[OCR] Tesseract binary not found; using EasyOCR fallback.")
            result = _extract_with_easyocr(processed_path)

        return result

    except Exception as e:
        logger.exception("[OCR] Unexpected error in extract_text.")
        return {"extracted_text": "", "confidence_score": 0.0,
                "success": False, "error": str(e)}

    finally:
        if processed_path != image_path and os.path.exists(processed_path):
            try:
                os.unlink(processed_path)
            except OSError:
                pass
