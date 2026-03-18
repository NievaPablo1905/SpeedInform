"""
Exportador de DOCX a PDF mediante Microsoft Word (COM / pywin32).

Solo funciona en Windows con Microsoft Word instalado.
En otros sistemas operativos lanza NotImplementedError.
"""

import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_pdf(docx_path: str) -> str:
    """
    Convierte un archivo DOCX a PDF usando Microsoft Word vía COM.

    Args:
        docx_path: Ruta absoluta al archivo DOCX.

    Returns:
        Ruta al archivo PDF generado (mismo directorio, mismo nombre base).

    Raises:
        NotImplementedError: Si no se está ejecutando en Windows.
        ImportError: Si pywin32 no está instalado.
        RuntimeError: Si Word no está disponible o falla la conversión.
    """
    if sys.platform != "win32":
        raise NotImplementedError(
            "La exportación a PDF vía COM solo está disponible en Windows con Microsoft Word."
        )

    try:
        import win32com.client as win32
    except ImportError as exc:
        raise ImportError(
            "pywin32 no está instalado. Ejecuta: pip install pywin32"
        ) from exc

    docx_path = str(Path(docx_path).resolve())
    pdf_path = str(Path(docx_path).with_suffix(".pdf"))

    word = None
    doc = None
    try:
        word = win32.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        doc = word.Documents.Open(docx_path)
        # wdFormatPDF = 17
        doc.SaveAs(pdf_path, FileFormat=17)
        logger.info("PDF exportado: %s", pdf_path)
    except Exception as exc:
        raise RuntimeError(f"Error al exportar PDF con Word: {exc}") from exc
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass

    return pdf_path
