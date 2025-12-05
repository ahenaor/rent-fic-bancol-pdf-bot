import logging
import os
from typing import Any, Dict

import yaml


# Load configuration
def load_config(config_path: str | None = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file with fallback support.

    Args:
        config_path: Path to config file. If None, tries CONFIG_PATH env var, then 'config.yaml'.

    Returns:
        Configuration dictionary.

    Raises:
        FileNotFoundError: If config file doesn't exist with helpful message.
        yaml.YAMLError: If config file is malformed.
    """
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "config.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"❌ Archivo de configuración no encontrado: {config_path}\n"
            f"   Asegúrate de que existe 'config.yaml' en el directorio raíz del proyecto,\n"
            f"   o define la variable de entorno CONFIG_PATH con la ruta correcta."
        )

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if config is None:
                raise ValueError("El archivo de configuración está vacío")
            return config
    except yaml.YAMLError as e:
        raise yaml.YAMLError(
            f"❌ Error al parsear el archivo de configuración {config_path}: {e}"
        )


# Load config at module level
CONFIG = load_config()

# Logging configuration
logging.basicConfig(
    level=getattr(logging, CONFIG["logging"]["level"]),
    format=CONFIG["logging"]["format"],
)

logger = logging.getLogger(__name__)

# Extract constants from config
MAX_RETRIES = CONFIG["download"]["max_retries"]
BACKOFF_BASE = CONFIG["download"]["backoff_base"]
URL_FIC = CONFIG["download"]["url"]
DOWNLOAD_TIMEOUT = CONFIG["download"]["timeout"]
JSON_STATUS_FILE = CONFIG["paths"]["json_status_file"]
DEBUG_FILE = CONFIG["paths"]["debug_file"]
RAW_PDF_BASE = CONFIG["paths"]["raw_pdf_base"]
PATRON_FECHA = CONFIG["date_patterns"]["primary"]
PATRON_FECHA_RESPALDO = CONFIG["date_patterns"]["fallback"]
MESES = CONFIG["months"]
