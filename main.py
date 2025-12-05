import io
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict

import requests
import yaml
from dotenv import load_dotenv
from llama_parse import LlamaParse
from pypdf import PdfReader, PdfWriter


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


def descargar_pdf(url: str, timeout: int = DOWNLOAD_TIMEOUT) -> bytes:
    """
    Download a PDF with automatic retries and exponential backoff.

    Args:
        url: URL of the PDF to download.
        timeout: Request timeout in seconds.

    Returns:
        PDF content as bytes.

    Raises:
        RuntimeError: If download fails after all retry attempts.
    """
    for intento in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200:
                return resp.content
            else:
                logger.warning(f"Intento {intento}: HTTP {resp.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Intento {intento}: error de red: {e}")

        if intento < MAX_RETRIES:
            wait_time = BACKOFF_BASE * (2 ** (intento - 1))
            logger.info(
                f"Esperando {wait_time} segundos antes del siguiente intento..."
            )
            time.sleep(wait_time)

    raise RuntimeError(f"No se pudo descargar el PDF tras {MAX_RETRIES} intentos")


def extraer_primera_pagina(content: bytes) -> io.BytesIO:
    """
    Extract the first page from a PDF.

    Args:
        content: PDF content as bytes.

    Returns:
        BytesIO object containing only the first page.
    """
    archivo_memoria = io.BytesIO(content)
    reader = PdfReader(archivo_memoria)
    writer = PdfWriter()

    if len(reader.pages) > 0:
        writer.add_page(reader.pages[0])
        pdf_hoja_1_memoria = io.BytesIO()
        writer.write(pdf_hoja_1_memoria)
        pdf_hoja_1_memoria.seek(0)
        return pdf_hoja_1_memoria

    raise ValueError("El PDF descargado está vacío")


def extraer_fecha_documento(texto: str) -> tuple[str, str, str] | None:
    """
    Extract publication date from document text using regex patterns.

    Args:
        texto: Markdown text extracted from PDF.

    Returns:
        Tuple of (day, month, year) if found, None otherwise.
    """
    # Try primary pattern
    match = re.search(PATRON_FECHA, texto, re.IGNORECASE)

    # Try fallback pattern if primary fails
    if not match:
        match = re.search(PATRON_FECHA_RESPALDO, texto, re.IGNORECASE)
        if match:
            logger.info("Fecha encontrada usando patrón de respaldo")

    if match:
        return match.groups()

    return None


def formatear_fecha(dia: str, mes: str, anio: str) -> str:
    """
    Format date components into YYYYMMDD format.

    Args:
        dia: Day as string.
        mes: Month name in Spanish.
        anio: Year as string.

    Returns:
        Formatted date string in YYYYMMDD format.

    Raises:
        ValueError: If month name is not recognized.
    """
    mes_numero = MESES.get(mes.lower())

    if not mes_numero:
        raise ValueError(f"Mes desconocido: {mes}")

    return f"{anio}{mes_numero}{dia.zfill(2)}"


def guardar_debug_markdown(texto: str) -> None:
    """
    Save markdown text to debug file for inspection.

    Args:
        texto: Markdown text to save.
    """
    try:
        os.makedirs(os.path.dirname(DEBUG_FILE), exist_ok=True)
        with open(DEBUG_FILE, "w", encoding="utf-8") as f:
            f.write(texto)
        logger.info(f"Markdown guardado en '{DEBUG_FILE}' para inspección")
    except Exception as e:
        logger.warning(f"No se pudo guardar el archivo de debug: {e}")


def procesar_pdf(
    content: bytes, parser: LlamaParse, fechas_procesadas: Dict[str, Any]
) -> bool:
    """
    Process PDF: extract date, check idempotency, and save if new.

    Args:
        content: PDF content as bytes.
        parser: LlamaParse instance for text extraction.
        fechas_procesadas: Dictionary with already processed dates.

    Returns:
        True if a new file was saved, False otherwise.
    """
    # Extract first page
    pdf_hoja_1_memoria = extraer_primera_pagina(content)

    # Extract text with LlamaParse
    logger.info("Analizando con LlamaParse...")
    documents = parser.load_data(
        pdf_hoja_1_memoria, extra_info={"file_name": "temp.pdf"}
    )

    # Defensive check: ensure LlamaParse returned documents
    if not documents:
        raise ValueError(
            "LlamaParse no devolvió ningún documento. "
            "Verifica la API key y el estado del servicio."
        )

    # Defensive check: ensure document has text attribute
    mk_hoja_01 = documents[0].text if documents[0].text else ""

    if not mk_hoja_01:
        logger.warning("LlamaParse devolvió un documento vacío")
        return False

    # Extract date from text
    fecha_tupla = extraer_fecha_documento(mk_hoja_01)

    if not fecha_tupla:
        logger.warning("No se encontró el patrón de fecha en el PDF. Revisa el Regex.")
        guardar_debug_markdown(mk_hoja_01)

        # Show text fragment for debugging
        logger.info("--- Primeros 500 caracteres del texto extraído ---")
        logger.info(mk_hoja_01[:500])
        logger.info("--- Fin del fragmento ---")
        return False

    dia, mes, anio = fecha_tupla
    fecha_formateada = formatear_fecha(dia, mes, anio)
    logger.info(f"Fecha detectada en documento: {fecha_formateada}")

    # Check idempotency
    if fecha_formateada in fechas_procesadas:
        logger.info(
            f"El archivo del {fecha_formateada} YA fue procesado anteriormente. Se omite descarga."
        )
        return False

    # Create directory structure based on document date
    target_folder = f"{RAW_PDF_BASE}/{anio}/{MESES[mes.lower()]}"
    os.makedirs(target_folder, exist_ok=True)

    # Save new file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{target_folder}/rentabilidades_fic_{fecha_formateada}_downloaded_{timestamp}.pdf"

    with open(filename, "wb") as f:
        f.write(content)

    logger.info(f"Nuevo archivo guardado: {filename}")

    # Update history
    fechas_procesadas[fecha_formateada] = {
        "downloaded_at": timestamp,
        "path": filename,
    }
    guardar_historial_procesado(fechas_procesadas)

    return True


def main() -> None:
    """Main function that executes the PDF download and processing workflow."""
    load_dotenv()

    LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
    if not LLAMA_CLOUD_API_KEY:
        raise ValueError(
            "❌ Error: No se encontró la variable de entorno LLAMA_CLOUD_API_KEY"
        )

    parser = LlamaParse(
        api_key=LLAMA_CLOUD_API_KEY,
        result_type=CONFIG["llama_parse"]["result_type"],
        verbose=CONFIG["llama_parse"]["verbose"],
        language=CONFIG["llama_parse"]["language"],
    )

    try:
        logger.info("Descargando PDF...")
        content = descargar_pdf(URL_FIC)

        fechas_procesadas = cargar_historial_procesado()
        nuevo_archivo = procesar_pdf(content, parser, fechas_procesadas)

        if nuevo_archivo:
            logger.info("✅ Se procesó y guardó un nuevo informe.")
        else:
            logger.info("ℹ️  No se encontró un nuevo informe para procesar.")

    except Exception:
        logger.exception("Error crítico")
    else:
        logger.info("Proceso completado correctamente.")


if __name__ == "__main__":
    main()
