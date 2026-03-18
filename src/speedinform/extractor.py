"""
Extractor de texto de PDFs e imágenes.

Pipeline:
1. Intenta extraer texto directamente del PDF con pdfminer.six.
   Si el texto obtenido tiene menos de 100 caracteres, recurre a OCR.
2. OCR: convierte el PDF a imágenes con pdf2image, aplica preprocesamiento
   básico con OpenCV (escala de grises + umbralización) si está disponible,
   y ejecuta pytesseract (lang='spa') en cada página.
3. Devuelve el texto combinado.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import pytesseract
    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False
    logger.warning("pytesseract no disponible; OCR desactivado.")

try:
    from pdf2image import convert_from_path
    _PDF2IMAGE_AVAILABLE = True
except ImportError:
    _PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image no disponible; conversión PDF→imagen desactivada.")

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

try:
    from pdfminer.high_level import extract_text as _pdfminer_extract
    _PDFMINER_AVAILABLE = True
except ImportError:
    _PDFMINER_AVAILABLE = False
    logger.warning("pdfminer.six no disponible; se usará OCR directamente.")

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def _preprocess_image(pil_image):
    """Aplica preprocesamiento OpenCV para mejorar el OCR."""
    if not _CV2_AVAILABLE or not _PIL_AVAILABLE:
        return pil_image
    img_array = np.array(pil_image.convert("RGB"))
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)


def _ocr_pdf(path: str) -> str:
    """Convierte un PDF a imágenes y extrae el texto con OCR."""
    if not _PDF2IMAGE_AVAILABLE:
        raise RuntimeError("pdf2image no está instalado. No se puede realizar OCR sobre PDF.")
    if not _TESSERACT_AVAILABLE:
        raise RuntimeError("pytesseract no está instalado. No se puede realizar OCR.")

    pages = convert_from_path(path, dpi=300)
    texts = []
    for page in pages:
        processed = _preprocess_image(page)
        text = pytesseract.image_to_string(processed, lang="spa")
        texts.append(text)
    return "\n".join(texts)


def _ocr_image(path: str) -> str:
    """Extrae texto de una imagen con OCR."""
    if not _TESSERACT_AVAILABLE:
        raise RuntimeError("pytesseract no está instalado. No se puede realizar OCR.")
    if not _PIL_AVAILABLE:
        raise RuntimeError("Pillow no está instalado.")

    img = Image.open(path)
    processed = _preprocess_image(img)
    return pytesseract.image_to_string(processed, lang="spa")


def _direct_pdf_text(path: str) -> str:
    """Extrae texto directamente del PDF usando pdfminer."""
    if not _PDFMINER_AVAILABLE:
        return ""
    try:
        return _pdfminer_extract(path) or ""
    except Exception as exc:
        logger.warning("pdfminer falló: %s", exc)
        return ""


def extract_text(path: str) -> str:
    """
    Extrae texto de un archivo PDF o imagen.

    Args:
        path: Ruta al archivo PDF o imagen.

    Returns:
        Texto extraído como cadena.
    """
    path = str(path)
    ext = Path(path).suffix.lower()

    if ext == ".pdf":
        text = _direct_pdf_text(path)
        if len(text.strip()) >= 100:
            logger.debug("Texto extraído directamente del PDF (%d chars).", len(text))
            return text
        logger.info("Texto insuficiente (%d chars); recurriendo a OCR.", len(text.strip()))
        return _ocr_pdf(path)

    image_exts = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif"}
    if ext in image_exts:
        return _ocr_image(path)

    raise ValueError(f"Formato de archivo no soportado: {ext}")
