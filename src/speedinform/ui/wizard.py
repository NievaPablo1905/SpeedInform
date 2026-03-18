"""
Asistente de 4 pasos para generar informes DGCIBER.

Paso 1 - Cargar Denuncia  : selector de archivo PDF o imagen.
Paso 2 - Procesando       : extracción de texto y parseo de campos (con barra de progreso).
Paso 3 - Revisar Datos    : formulario editable con los 9 campos principales.
Paso 4 - Generar Documentos: botón "Generar Word" y botón opcional "Exportar PDF".
"""

import os
import logging
import sys

from PySide6.QtWidgets import (
    QWizard,
    QWizardPage,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QFormLayout,
    QScrollArea,
    QWidget,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont

from ..extractor import extract_text
from ..parser import parse_fields
from ..generator import generate_documents
from ..case import save_case, case_name_from_nro, create_case_dir

logger = logging.getLogger(__name__)

# IDs de páginas del wizard
PAGE_CARGAR = 0
PAGE_PROCESANDO = 1
PAGE_REVISAR = 2
PAGE_GENERAR = 3


class _ExtractionWorker(QObject):
    """Worker que ejecuta la extracción y parseo en un hilo separado."""

    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(int, str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.progress.emit(20, "Extrayendo texto del archivo…")
            text = extract_text(self.file_path)
            self.progress.emit(70, "Analizando campos de la denuncia…")
            fields = parse_fields(text)
            fields["_source_file"] = self.file_path
            fields["_raw_text"] = text
            self.progress.emit(100, "Listo.")
            self.finished.emit(fields)
        except Exception as exc:
            self.error.emit(str(exc))


# ─── Página 1: Cargar Denuncia ───────────────────────────────────────────────

class PageCargar(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Paso 1: Cargar Denuncia")
        self.setSubTitle(
            "Seleccione el archivo PDF o imagen de la denuncia DGCIBER."
        )
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        file_row = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Ruta del archivo…")
        self.file_edit.setReadOnly(True)
        self.registerField("source_file*", self.file_edit)
        file_row.addWidget(self.file_edit)

        btn_browse = QPushButton("Examinar…")
        btn_browse.clicked.connect(self._browse)
        file_row.addWidget(btn_browse)
        layout.addLayout(file_row)

        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)
        layout.addWidget(self.lbl_info)
        layout.addStretch()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar denuncia",
            "",
            "Archivos compatibles (*.pdf *.png *.jpg *.jpeg *.tiff *.tif *.bmp);;Todos (*)",
        )
        if path:
            self.file_edit.setText(path)
            self.lbl_info.setText(f"Archivo seleccionado: {os.path.basename(path)}")


# ─── Página 2: Procesando ────────────────────────────────────────────────────

class PageProcesando(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Paso 2: Procesando")
        self.setSubTitle("Extrayendo texto y analizando los campos de la denuncia.")
        self._fields: dict = {}
        self._done = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        self.lbl_status = QLabel("Esperando…")
        layout.addWidget(self.lbl_status)
        layout.addStretch()

    def initializePage(self):
        self._done = False
        self._fields = {}
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Iniciando…")
        self.completeChanged.emit()

        file_path = self.field("source_file")
        self._thread = QThread()
        self._worker = _ExtractionWorker(file_path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)

    def _on_finished(self, fields: dict):
        self._fields = fields
        self._done = True
        self.lbl_status.setText("Procesamiento completado.")
        self.completeChanged.emit()
        # Auto-avanzar al siguiente paso
        self.wizard().next()

    def _on_error(self, message: str):
        self._done = True
        self.lbl_status.setText(f"Error: {message}")
        self.completeChanged.emit()
        QMessageBox.critical(self, "Error de procesamiento", message)

    def isComplete(self) -> bool:
        return self._done

    def get_fields(self) -> dict:
        return self._fields


# ─── Página 3: Revisar Datos ─────────────────────────────────────────────────

class PageRevisar(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Paso 3: Revisar Datos")
        self.setSubTitle(
            "Revise y corrija los campos extraídos antes de generar los documentos."
        )
        self._build_ui()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)

        self.lbl_warning = QLabel("")
        self.lbl_warning.setWordWrap(True)
        self.lbl_warning.setStyleSheet("color: orange; font-weight: bold;")
        outer_layout.addWidget(self.lbl_warning)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        form.setSpacing(8)

        def make_line(key: str) -> QLineEdit:
            le = QLineEdit()
            self.registerField(key, le)
            return le

        self.f_nro = make_line("nro")
        self.f_s = make_line("s")
        self.f_p = make_line("p")
        self.f_c = make_line("c")
        self.f_fecha = make_line("fecha_hecho")
        self.f_hora = make_line("hora_hecho")
        self.f_lugar = make_line("lugar")
        self.f_fiscal = make_line("fiscal")

        self.f_relato = QTextEdit()
        self.f_relato.setMinimumHeight(120)
        self.f_relato.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        form.addRow("Nro. Expediente:", self.f_nro)
        form.addRow("Carátula (S):", self.f_s)
        form.addRow("Víctima (P):", self.f_p)
        form.addRow("Denunciado (C):", self.f_c)
        form.addRow("Fecha del Hecho:", self.f_fecha)
        form.addRow("Hora del Hecho:", self.f_hora)
        form.addRow("Lugar del Hecho:", self.f_lugar)
        form.addRow("Fiscal:", self.f_fiscal)
        form.addRow("Relato:", self.f_relato)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def initializePage(self):
        # Obtener campos del paso anterior
        proc_page: PageProcesando = self.wizard().page(PAGE_PROCESANDO)
        fields = proc_page.get_fields()

        self.f_nro.setText(fields.get("nro", ""))
        self.f_s.setText(fields.get("s", ""))
        self.f_p.setText(fields.get("p", ""))
        self.f_c.setText(fields.get("c", "NN"))
        self.f_fecha.setText(fields.get("fecha_hecho", ""))
        self.f_hora.setText(fields.get("hora_hecho", ""))
        self.f_lugar.setText(fields.get("lugar", ""))
        self.f_fiscal.setText(fields.get("fiscal", ""))
        self.f_relato.setPlainText(fields.get("relato", ""))

        # Advertencia si NRO actuación ≠ NRO denuncia
        nro_d = fields.get("nro_denuncia", "")
        nro_a = fields.get("nro_actuacion", "")
        if nro_d and nro_a and nro_d != nro_a:
            self.lbl_warning.setText(
                f"⚠ Atención: el Nro. de denuncia ({nro_d}) difiere del Nro. de actuación ({nro_a}). "
                "Verifique cuál es el correcto."
            )
        else:
            self.lbl_warning.setText("")

    def get_current_fields(self) -> dict:
        return {
            "nro": self.f_nro.text().strip(),
            "s": self.f_s.text().strip(),
            "p": self.f_p.text().strip(),
            "c": self.f_c.text().strip() or "NN",
            "fecha_hecho": self.f_fecha.text().strip(),
            "hora_hecho": self.f_hora.text().strip(),
            "lugar": self.f_lugar.text().strip(),
            "fiscal": self.f_fiscal.text().strip(),
            "relato": self.f_relato.toPlainText().strip(),
        }


# ─── Página 4: Generar Documentos ────────────────────────────────────────────

class PageGenerar(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Paso 4: Generar Documentos")
        self.setSubTitle("Genere los documentos Word y, opcionalmente, expórtelos a PDF.")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        btn_row = QHBoxLayout()
        self.btn_word = QPushButton("Generar Word")
        self.btn_word.setMinimumHeight(40)
        self.btn_word.clicked.connect(self._generar_word)
        btn_row.addWidget(self.btn_word)

        self.btn_pdf = QPushButton("Exportar PDF")
        self.btn_pdf.setMinimumHeight(40)
        self.btn_pdf.setEnabled(False)
        self.btn_pdf.clicked.connect(self._exportar_pdf)
        btn_row.addWidget(self.btn_pdf)

        layout.addLayout(btn_row)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.lbl_output = QLabel("")
        self.lbl_output.setWordWrap(True)
        layout.addWidget(self.lbl_output)

        self._generated_paths: list[str] = []

    def initializePage(self):
        self.log_area.clear()
        self._generated_paths = []
        self.btn_pdf.setEnabled(False)
        self.lbl_output.setText("")
        self.btn_word.setEnabled(True)

    def _log(self, msg: str):
        self.log_area.append(msg)

    def _generar_word(self):
        self.btn_word.setEnabled(False)
        wizard: InformeWizard = self.wizard()

        revisar_page: PageRevisar = wizard.page(PAGE_REVISAR)
        fields = revisar_page.get_current_fields()

        output_dir = os.path.join(wizard.case_dir, "salida")
        os.makedirs(output_dir, exist_ok=True)

        self._log("Generando documentos Word…")
        try:
            paths = generate_documents(
                template_path=None,
                fields=fields,
                output_dir=output_dir,
            )
            self._generated_paths = paths
            for p in paths:
                self._log(f"✓ {os.path.basename(p)}")
            self._log(f"\nGuardados en: {output_dir}")
            self.lbl_output.setText(f"Documentos guardados en:\n{output_dir}")

            # Guardar caso
            all_fields = dict(fields)
            all_fields["_output_dir"] = output_dir
            proc_page: PageProcesando = wizard.page(PAGE_PROCESANDO)
            raw_fields = proc_page.get_fields()
            all_fields["_raw_text"] = raw_fields.get("_raw_text", "")
            all_fields["_source_file"] = raw_fields.get("_source_file", "")
            save_case(wizard.case_dir, all_fields)
            self._log("Caso guardado en caso.json.")

            if sys.platform == "win32":
                self.btn_pdf.setEnabled(True)
        except Exception as exc:
            self._log(f"✗ Error: {exc}")
            QMessageBox.critical(self, "Error al generar", str(exc))
            self.btn_word.setEnabled(True)

    def _exportar_pdf(self):
        if not self._generated_paths:
            return
        self.btn_pdf.setEnabled(False)
        self._log("\nExportando a PDF…")
        try:
            from ..exporter import export_pdf
            for docx_path in self._generated_paths:
                pdf_path = export_pdf(docx_path)
                self._log(f"✓ PDF: {os.path.basename(pdf_path)}")
        except NotImplementedError as exc:
            self._log(f"✗ {exc}")
            QMessageBox.information(self, "No disponible", str(exc))
        except Exception as exc:
            self._log(f"✗ Error al exportar PDF: {exc}")
            QMessageBox.critical(self, "Error al exportar", str(exc))
        finally:
            self.btn_pdf.setEnabled(True)


# ─── Wizard principal ─────────────────────────────────────────────────────────

class InformeWizard(QWizard):
    """Asistente de 4 pasos para generar un informe DGCIBER."""

    def __init__(self, case_dir: str, preloaded_data: dict | None = None, parent=None):
        super().__init__(parent)
        self.case_dir = case_dir
        self.preloaded_data = preloaded_data or {}

        self.setWindowTitle("Nuevo Informe — SpeedInform")
        self.setMinimumSize(700, 520)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self._page_cargar = PageCargar()
        self._page_procesando = PageProcesando()
        self._page_revisar = PageRevisar()
        self._page_generar = PageGenerar()

        self.setPage(PAGE_CARGAR, self._page_cargar)
        self.setPage(PAGE_PROCESANDO, self._page_procesando)
        self.setPage(PAGE_REVISAR, self._page_revisar)
        self.setPage(PAGE_GENERAR, self._page_generar)

        self.setStartId(PAGE_CARGAR)

        # Si hay datos precargados, saltarse los pasos de extracción
        if self.preloaded_data:
            self._inject_preloaded()

    def _inject_preloaded(self):
        """Inyecta datos precargados en la página de procesado para reutilizarlos."""
        self._page_procesando._fields = self.preloaded_data
        self._page_procesando._done = True
