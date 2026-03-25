"""
Persistencia de casos.

Cada caso se almacena como una carpeta en:
  ~/Documents/SpeedInform/Casos/{nombre_caso}/

Dentro de la carpeta:
  - caso.json   : campos extraídos + metadatos
  - salida/     : documentos Word y PDF generados
"""

import json
import os
import re
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_APP_NAME = "SpeedInform"
_CASES_SUBDIR = os.path.join("Documents", _APP_NAME, "Casos")


def get_default_cases_dir() -> str:
    """Devuelve el directorio raíz donde se almacenan los casos."""
    home = Path.home()
    return str(home / "Documents" / _APP_NAME / "Casos")


def create_case_dir(case_name: str) -> str:
    """
    Crea y devuelve el directorio para un caso nuevo.

    Args:
        case_name: Nombre del caso (se sanitiza para uso en el sistema de archivos).

    Returns:
        Ruta absoluta al directorio del caso.
    """
    safe_name = re.sub(r"[^\w\-_. ]", "_", case_name).strip()
    case_dir = os.path.join(get_default_cases_dir(), safe_name)
    os.makedirs(case_dir, exist_ok=True)
    os.makedirs(os.path.join(case_dir, "salida"), exist_ok=True)
    return case_dir


def case_name_from_nro(nro: str) -> str:
    """Genera un nombre de carpeta a partir del número de expediente."""
    if not nro:
        return f"Caso_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    safe = nro.replace("/", "_")
    return f"Caso_{safe}"


def save_case(case_dir: str, data: dict) -> None:
    """
    Guarda los datos del caso en caso.json dentro de case_dir.

    Args:
        case_dir: Directorio del caso.
        data: Diccionario con los campos del caso.
    """
    os.makedirs(case_dir, exist_ok=True)
    data_to_save = dict(data)
    data_to_save["_updated_at"] = datetime.now().isoformat()
    if "_created_at" not in data_to_save:
        data_to_save["_created_at"] = data_to_save["_updated_at"]

    path = os.path.join(case_dir, "caso.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    logger.info("Caso guardado en: %s", path)


def load_case(case_dir: str) -> dict:
    """
    Carga los datos del caso desde caso.json.

    Args:
        case_dir: Directorio del caso.

    Returns:
        Diccionario con los datos del caso.

    Raises:
        FileNotFoundError: Si caso.json no existe.
    """
    path = os.path.join(case_dir, "caso.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró caso.json en: {case_dir}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
