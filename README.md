# SpeedInform

Aplicación de escritorio (Windows) para agilizar la confección de informes en **formato Word (.docx)**, a partir de una **denuncia penal** cargada como **PDF** o **imágenes**.

## Funcionalidades (MVP)

- **Cargar denuncia**: PDF o imágenes (JPG/PNG/TIFF/BMP).
- **OCR offline**: para PDFs escaneados usa Tesseract + pdf2image con preprocesamiento OpenCV.
- **Extracción automática de campos**: carátula, lugar, fecha/hora, víctima, denunciado, fiscal, relato.
- **Vista previa y edición**: formulario editable antes de generar los documentos.
- **Generación de 3 documentos Word**:
  - `informe.docx`
  - `avocamiento.docx`
  - `elevacion.docx`
- **Exportación a PDF** mediante Microsoft Word (COM/pywin32, solo Windows).
- **Persistencia de casos**: cada caso se guarda en `~/Documents/SpeedInform/Casos/`.

## Requisitos

### Python 3.11+

Descargue e instale Python 3.11 o superior desde [python.org](https://www.python.org/downloads/).

### Dependencias Python

```bash
pip install -r requirements.txt
```

### Tesseract OCR (con idioma español)

1. Descargue el instalador desde [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
2. Durante la instalación, seleccione el paquete de idioma **Spanish (spa)**.
3. Asegúrese de que `tesseract` esté en el `PATH` del sistema, o configure la ruta en `pytesseract.pytesseract.tesseract_cmd`.

### Poppler (para convertir PDF a imágenes)

Necesario para `pdf2image`:

1. Descargue Poppler para Windows desde [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases).
2. Extraiga el contenido y agregue la carpeta `bin/` al `PATH` del sistema.

### Microsoft Word (para exportar a PDF)

- Requerido **solo** para la funcionalidad de exportación a PDF.
- Se usa la interfaz COM (pywin32) para abrir el `.docx` con Word y guardarlo como PDF.
- Si Word no está instalado, los documentos `.docx` se generan igualmente; solo la exportación a PDF no estará disponible.

## Instalación y uso

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd SpeedInform

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python -m speedinform
```

O si instalaste el paquete con `pip install -e .`:

```bash
speedinform
```

## Estructura del proyecto

```
SpeedInform/
├── src/speedinform/
│   ├── __init__.py
│   ├── __main__.py       # Punto de entrada
│   ├── extractor.py      # Extracción de texto (PDF/OCR)
│   ├── parser.py         # Parseo de campos DGCIBER
│   ├── generator.py      # Generación de DOCX desde plantilla
│   ├── exporter.py       # Exportación a PDF (pywin32/COM)
│   ├── case.py           # Persistencia de casos (caso.json)
│   └── ui/
│       ├── main_window.py  # Ventana principal
│       └── wizard.py       # Asistente de 4 pasos
├── tests/
│   └── test_parser.py
├── PLANTILLA INFORME PARA PROGRAM.docx
├── requirements.txt
└── pyproject.toml
```

## Plantilla DOCX

La plantilla `PLANTILLA INFORME PARA PROGRAM.docx` debe contener:

- **Marcadores de sección**: `[[INICIO_INFORME]]`, `[[INICIO_AVOCAMIENTO]]`, `[[INICIO_ELEVACION]]`
- **Marcadores de campo**: `{{nro}}`, `{{s}}`, `{{p}}`, `{{c}}`, `{{fecha_hecho}}`, `{{hora_hecho}}`, `{{lugar}}`, `{{fiscal}}`, `{{relato}}`

## Tests

```bash
python -m pytest tests/
```