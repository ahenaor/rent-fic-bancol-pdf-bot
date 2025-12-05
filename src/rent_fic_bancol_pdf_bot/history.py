import json
import os
from typing import Any, Dict

from .config import JSON_STATUS_FILE, logger


def cargar_historial_procesado() -> Dict[str, Any]:
    """
    Load the JSON file with processed dates history.

    Returns:
        Dictionary with processed dates. Empty dict if file doesn't exist or is corrupted.
    """
    if os.path.exists(JSON_STATUS_FILE):
        try:
            with open(JSON_STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            backup_path = JSON_STATUS_FILE + ".bak"
            os.replace(JSON_STATUS_FILE, backup_path)
            logger.warning(
                f"Archivo JSON corrupto. Se movió a {backup_path}. Iniciando historial vacío."
            )
            return {}
    return {}


def guardar_historial_procesado(historial: Dict[str, Any]) -> None:
    """
    Save the updated dictionary to the JSON file.

    Args:
        historial: Dictionary with processed dates history.
    """
    os.makedirs(os.path.dirname(JSON_STATUS_FILE), exist_ok=True)
    with open(JSON_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=4, ensure_ascii=False)
