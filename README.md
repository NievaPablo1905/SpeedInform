# SpeedInform

Aplicación de escritorio (Windows) para agilizar la confección de informes en **formato Word (.docx)**, a partir de una **denuncia penal** cargada como **PDF** o **imágenes**.

## Funcionalidades (MVP)
- Cargar denuncia: PDF o imágenes (JPG/PNG)
- OCR (offline) para PDFs escaneados
- Extracción de campos (carátula, lugar, fecha/hora, partes, relato)
- Vista previa y edición manual de los campos detectados
- Generación de documentos:
  - Constancia de avocamiento
  - Informe con secciones (banda azul)
  - Nota de elevación
- Salida:
  - Word (.docx) con **Times New Roman 12** y formato idéntico a la plantilla
  - Exportación a PDF usando Microsoft Word (instalado en las PCs objetivo)

## Requisitos (Windows)
### 1) Python
- Python 3.11+ recomendado.

### 2) Dependencias Python
```bash
pip install -r requirements.txt
```

### 3) Tesseract OCR
- Instalar Tesseract (español) y asegurarse de tener el paquete de idioma `spa`.

### 4) Poppler (para convertir PDF a imágenes)
- Necesario para `pdf2image`.

### 5) Microsoft Word
- Se utiliza para exportar .docx a PDF con alta fidelidad.

## Estado
Repositorio inicial (en construcción). Próximos pasos: agregar estructura del proyecto, GUI, OCR y generador DOCX.