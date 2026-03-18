"""
Parser de campos en formato DGCIBER.

Extrae los siguientes campos del texto de la denuncia:
  - nro            : número normalizado "NN/AAAA" (primer número encontrado)
  - nro_denuncia   : ídem nro
  - nro_actuacion  : número de actuación si difiere del de denuncia
  - s              : carátula / objeto del proceso
  - p              : víctima / damnificado
  - c              : denunciado / sospechoso (default "NN")
  - fecha_hecho    : parte fecha de FECHA-HORA-HECHO
  - hora_hecho     : parte hora de FECHA-HORA-HECHO
  - lugar          : lugar del hecho
  - fiscal         : fiscal interviniente
  - relato         : relato del hecho (entre declaración art.245 y aviso a víctima)
"""

import re
import unicodedata
import logging

logger = logging.getLogger(__name__)


def _strip_accents(text: str) -> str:
    """Elimina tildes/diacríticos para comparaciones tolerantes."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def normalize_nro(raw: str) -> str:
    """
    Normaliza un número de expediente al formato "NN/AAAA".

    - Elimina espacios alrededor de la barra.
    - Elimina ceros a la izquierda del número.

    >>> normalize_nro("57 / 2026")
    '57/2026'
    >>> normalize_nro("007 / 2026")
    '7/2026'
    """
    raw = raw.strip()
    raw = re.sub(r"\s*/\s*", "/", raw)
    parts = raw.split("/")
    if len(parts) == 2:
        try:
            num = str(int(parts[0]))
        except ValueError:
            num = parts[0]
        return f"{num}/{parts[1].strip()}"
    return raw


def _find_field(pattern: str, text: str, flags: int = re.IGNORECASE) -> str:
    """Ejecuta una regex y devuelve el primer grupo capturado, o ''."""
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else ""


def _tol(label: str) -> str:
    """
    Construye un patrón de regex tolerante a OCR para una etiqueta:
      - ignora tildes (comparación en ASCII)
      - permite espacios variables entre palabras
    """
    # Normalizar la etiqueta a ASCII
    label_ascii = _strip_accents(label)
    # Escapar caracteres especiales y reemplazar espacios por \s+
    escaped = re.escape(label_ascii)
    escaped = escaped.replace(r"\ ", r"\s*")
    # Wrappear para que funcione contra texto también sin tildes
    return escaped


def _search_tol(label: str, text: str) -> re.Match | None:
    """Busca una etiqueta tolerante a tildes en el texto (también sin tildes)."""
    pattern = _tol(label)
    text_ascii = _strip_accents(text)
    return re.search(pattern, text_ascii, re.IGNORECASE)


def _extract_after_label(label: str, text: str, multiline_end: str | None = None) -> str:
    """
    Extrae el valor que sigue a una etiqueta en el texto.
    Tolerante a tildes y espacios variables.
    """
    text_ascii = _strip_accents(text)
    label_ascii = _strip_accents(label)
    # Construir patrón: etiqueta seguida de posible ':' y espacios, luego el valor
    escaped = re.escape(label_ascii).replace(r"\ ", r"\s+")
    pattern = rf"{escaped}\s*:?\s*(.+?)(?=\n|\Z)"
    if multiline_end:
        end_ascii = _strip_accents(multiline_end)
        end_esc = re.escape(end_ascii).replace(r"\ ", r"\s+")
        pattern = rf"{escaped}\s*:?\s*(.+?)(?={end_esc}|\Z)"
        m = re.search(pattern, text_ascii, re.IGNORECASE | re.DOTALL)
    else:
        m = re.search(pattern, text_ascii, re.IGNORECASE)

    if not m:
        return ""
    start = m.start(1)
    end = m.end(1)
    return text[start:end].strip()


def _extract_section_value(section_keyword: str, field_keyword: str, text: str) -> str:
    """
    Busca 'field_keyword' dentro de la sección que comienza con 'section_keyword'.
    Devuelve el valor encontrado o ''.
    """
    text_ascii = _strip_accents(text)
    sec_ascii = _strip_accents(section_keyword)
    field_ascii = _strip_accents(field_keyword)

    sec_esc = re.escape(sec_ascii).replace(r"\ ", r"\s+")
    field_esc = re.escape(field_ascii).replace(r"\ ", r"\s+")

    # Encontrar inicio de sección
    m_sec = re.search(sec_esc, text_ascii, re.IGNORECASE)
    if not m_sec:
        return ""

    section_text = text_ascii[m_sec.start():]
    original_section = text[m_sec.start():]

    pattern = rf"{field_esc}\s*:?\s*([^\n]+)"
    m = re.search(pattern, section_text, re.IGNORECASE)
    if not m:
        return ""
    start = m.start(1)
    end = m.end(1)
    return original_section[start:end].strip()


def parse_fields(text: str) -> dict:
    """
    Parsea los campos del formato DGCIBER desde el texto de la denuncia.

    Args:
        text: Texto extraído del PDF o imagen.

    Returns:
        Diccionario con las claves:
        nro, nro_denuncia, nro_actuacion, s, p, c,
        fecha_hecho, hora_hecho, lugar, fiscal, relato.
    """
    fields: dict = {
        "nro": "",
        "nro_denuncia": "",
        "nro_actuacion": "",
        "s": "",
        "p": "",
        "c": "NN",
        "fecha_hecho": "",
        "hora_hecho": "",
        "lugar": "",
        "fiscal": "",
        "relato": "",
    }

    text_ascii = _strip_accents(text)

    # ── NRO denuncia ──────────────────────────────────────────────────────────
    m_nro = re.search(
        r"DENUNCIA\s+PENAL\s+DGCIBER\s*[-–]\s*(\d+\s*/\s*\d+)",
        text_ascii,
        re.IGNORECASE,
    )
    if m_nro:
        raw = m_nro.group(1)
        start = m_nro.start(1)
        fields["nro_denuncia"] = normalize_nro(text[start : start + len(raw)])
        fields["nro"] = fields["nro_denuncia"]

    # ── NRO actuación (puede diferir) ─────────────────────────────────────────
    m_act = re.search(
        r"(?:ACTUACION|ACTUACIÓN)\s*[Nn]°?\s*[:\-]?\s*(\d+\s*/\s*\d+)",
        text_ascii,
        re.IGNORECASE,
    )
    if m_act:
        raw = m_act.group(1)
        start = m_act.start(1)
        fields["nro_actuacion"] = normalize_nro(text[start : start + len(raw)])
        if not fields["nro"]:
            fields["nro"] = fields["nro_actuacion"]

    # ── S: Carátula ───────────────────────────────────────────────────────────
    m_s = re.search(
        r"CARATULA\s+INICIAL\s*:?\s*(.+?)(?=\n|$)",
        text_ascii,
        re.IGNORECASE,
    )
    if m_s:
        start, end = m_s.start(1), m_s.end(1)
        fields["s"] = text[start:end].strip()

    # ── P: Víctima ────────────────────────────────────────────────────────────
    # Busca sección VICTIMA/DAMNIFICADO y dentro de ella -APELLIDO Y NOMBRE:
    victim_section_match = re.search(
        r"VICTIMA\s*/?\s*DAMNIFICADO",
        text_ascii,
        re.IGNORECASE,
    )
    if victim_section_match:
        section_start = victim_section_match.start()
        # Próxima sección grande (todo en mayúsculas aislado) como límite
        section_text_ascii = text_ascii[section_start:]
        section_text_orig = text[section_start:]
        m_p = re.search(
            r"-?\s*APELLIDO\s+Y\s+NOMBRE\s*:?\s*([^\n]+)",
            section_text_ascii,
            re.IGNORECASE,
        )
        if m_p:
            start, end = m_p.start(1), m_p.end(1)
            fields["p"] = section_text_orig[start:end].strip()

    # ── C: Denunciado ─────────────────────────────────────────────────────────
    denunciado_match = re.search(
        r"DENUNCIADO\s*/?\s*SOSPECHOSO",
        text_ascii,
        re.IGNORECASE,
    )
    if denunciado_match:
        section_start = denunciado_match.start()
        section_text_ascii = text_ascii[section_start:]
        section_text_orig = text[section_start:]
        m_c = re.search(
            r"-?\s*APELLIDO\s+Y\s+NOMBRE\s*:?\s*([^\n]+)",
            section_text_ascii,
            re.IGNORECASE,
        )
        if m_c:
            val = section_text_orig[m_c.start(1) : m_c.end(1)].strip()
            if val:
                fields["c"] = val

    # ── Fecha y hora del hecho ────────────────────────────────────────────────
    m_fh = re.search(
        r"FECHA\s*-\s*HORA\s*-\s*HECHO\s*:?\s*(\S+)\s+(\S+)",
        text_ascii,
        re.IGNORECASE,
    )
    if m_fh:
        # Obtener posiciones en el texto original
        start1, end1 = m_fh.start(1), m_fh.end(1)
        start2, end2 = m_fh.start(2), m_fh.end(2)
        fields["fecha_hecho"] = text[start1:end1].strip()
        fields["hora_hecho"] = text[start2:end2].strip()

    # ── Lugar del hecho ───────────────────────────────────────────────────────
    m_lugar = re.search(
        r"LUGAR\s+DEL\s+HECHO\s*:?\s*(.+?)(?=\n|$)",
        text_ascii,
        re.IGNORECASE,
    )
    if m_lugar:
        start, end = m_lugar.start(1), m_lugar.end(1)
        fields["lugar"] = text[start:end].strip()

    # ── Fiscal ────────────────────────────────────────────────────────────────
    m_fiscal = re.search(
        r"FISCAL\s+INTERVINIENTE\s*:?\s*(.+?)(?=\n|$)",
        text_ascii,
        re.IGNORECASE,
    )
    if m_fiscal:
        start, end = m_fiscal.start(1), m_fiscal.end(1)
        fields["fiscal"] = text[start:end].strip()

    # ── Relato ────────────────────────────────────────────────────────────────
    # Desde "CON PLENO CONOCIMIENTO DEL ART(E?). 245 DEL CPP"
    # hasta "INFORMACIÓN QUE SE LE BRINDA A LA VÍCTIMA" o fin
    m_relato_start = re.search(
        r"CON\s+PLENO\s+CONOCIMIENTO\s+DEL\s+ARTE?\.\s*245\s+DEL\s+CPP[^\n]*\n",
        text_ascii,
        re.IGNORECASE,
    )
    m_relato_end = re.search(
        r"INFORMACION\s+QUE\s+SE\s+LE\s+BRINDA\s+A\s+LA\s+VICTIMA",
        text_ascii,
        re.IGNORECASE,
    )
    if m_relato_start:
        r_start = m_relato_start.end()
        r_end = m_relato_end.start() if m_relato_end else len(text)
        fields["relato"] = text[r_start:r_end].strip()

    return fields
