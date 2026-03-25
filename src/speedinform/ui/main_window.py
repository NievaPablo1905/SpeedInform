"""
Ventana principal de SpeedInform.

Presenta dos opciones:
  - Nuevo Informe   : crea un nuevo caso y abre el asistente.
  - Abrir Informe…  : selecciona una carpeta de caso existente y abre el asistente.
"""

import os
import logging
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..case import (
    create_case_dir,
    load_case,
    get_default_cases_dir,
    case_name_from_nro,
)
from .wizard import InformeWizard

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Ventana principal de SpeedInform."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SpeedInform")
        self.setMinimumSize(480, 320)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(24)
        layout.setContentsMargins(40, 40, 40, 40)

        # Título
        title = QLabel("SpeedInform")
        font = QFont()
        font.setPointSize(22)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Generador de Informes DGCIBER")
        sub_font = QFont()
        sub_font.setPointSize(11)
        subtitle.setFont(sub_font)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addStretch()

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)

        self.btn_nuevo = QPushButton("Nuevo Informe")
        self.btn_nuevo.setMinimumHeight(48)
        self.btn_nuevo.setMinimumWidth(160)
        btn_font = QFont()
        btn_font.setPointSize(12)
        self.btn_nuevo.setFont(btn_font)
        self.btn_nuevo.clicked.connect(self._on_nuevo_informe)
        btn_layout.addWidget(self.btn_nuevo)

        self.btn_abrir = QPushButton("Abrir Informe…")
        self.btn_abrir.setMinimumHeight(48)
        self.btn_abrir.setMinimumWidth(160)
        self.btn_abrir.setFont(btn_font)
        self.btn_abrir.clicked.connect(self._on_abrir_informe)
        btn_layout.addWidget(self.btn_abrir)

        layout.addLayout(btn_layout)
        layout.addStretch()

        version_label = QLabel("v0.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(version_label)

    def _on_nuevo_informe(self):
        """Crea un nuevo caso y abre el asistente."""
        case_name, ok = QInputDialog.getText(
            self,
            "Nuevo Informe",
            "Nombre del caso (se usará como nombre de carpeta):\n"
            "(Dejar vacío para generar automáticamente desde el número de denuncia)",
        )
        if not ok:
            return

        if not case_name.strip():
            # Se asignará cuando se conozca el NRO; por ahora usar timestamp
            case_name = f"Caso_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            case_dir = create_case_dir(case_name.strip())
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo crear la carpeta del caso:\n{exc}")
            return

        wizard = InformeWizard(case_dir=case_dir, parent=self)
        wizard.exec()

    def _on_abrir_informe(self):
        """Abre un informe existente seleccionando su carpeta."""
        start_dir = get_default_cases_dir()
        os.makedirs(start_dir, exist_ok=True)

        case_dir = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta del informe",
            start_dir,
        )
        if not case_dir:
            return

        try:
            data = load_case(case_dir)
        except FileNotFoundError:
            QMessageBox.warning(
                self,
                "Carpeta inválida",
                f"No se encontró caso.json en:\n{case_dir}\n\n"
                "Seleccione una carpeta de caso válida.",
            )
            return
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el caso:\n{exc}")
            return

        wizard = InformeWizard(case_dir=case_dir, preloaded_data=data, parent=self)
        wizard.exec()
