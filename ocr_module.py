"""
ocr_module.py — Tesseract OCR wrapper for VeriNews
Extracts text from uploaded screenshot images using Tesseract OCR.
"""
import os
import tempfile
import logging
import platform

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

if platform.system() == "Windows":
    # Default Windows installation path
    TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    # On Linux/Docker, it's typically in the PATH
    TESSERACT_CMD = "tesseract"

MAX_SIDE_PX   = 1200    # resize so longest side ≤ this
AUTO_INVERT   = True    # flip dark-background images to dark-text-on-white

# Tesseract config: page segmentation mode 3 (fully automatic)
TESS_CONFIG   = "--psm 3 -l eng"

# ── Compatibility flags (for the /ocr-status endpoint) ────────────────────────
_reader_ready = True
_reader       = True

def warmup():
    """No-op: Tesseract needs no warmup."""
    pass

# ── Image pre-processing ──────────────────────────────────────────────────────

def _preprocess_image(image_path: str) -> str:
    """
    Prepare image for Tesseract:
      1. Resize so longest side ≤ MAX_SIDE_PX
      2. Convert to grayscale
      3. Auto-invert dark-background images
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
        
        # On Linux (Docker), 'tesseract' is in PATH. On Windows, we set it manually.
        if platform.system() == "Windows":
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
            try:
                conf = int(data["conf"][i])
            except (ValueError, TypeError):
                conf = -1
                
            if conf > 0 and word.strip():
                words.append(word.strip())
                confidences.append(conf / 100.0)

        if not words:
            return {
                "extracted_text": "",
                "confidence_score": 0.0,
                "success": False,
                "error": "Tesseract returned no text content."
            }

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
        return {
            "extracted_text": "",
            "confidence_score": 0.0,
            "success": False,
            "error": f"OCR Error: {str(e)}"
        }

# ── Public API ────────────────────────────────────────────────────────────────

def extract_text(image_path: str) -> dict:
    """
    Extract text from an image file using Tesseract.
    """
    if not os.path.exists(image_path):
        return {"extracted_text": "", "confidence_score": 0.0,
                "success": False, "error": f"File not found: {image_path}"}

    processed_path = image_path
    try:
        processed_path = _preprocess_image(image_path)
        return _extract_with_tesseract(processed_path)

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
