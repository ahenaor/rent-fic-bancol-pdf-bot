import io
import os
import re
from datetime import datetime
from typing import Any, Dict

from llama_parse import LlamaParse
from pypdf import PdfReader, PdfWriter

from .config import (
    DEBUG_FILE,
    MESES,
    PATRON_FECHA,
    PATRON_FECHA_RESPALDO,
    RAW_PDF_BASE,
    logger,
)
from .history import guardar_historial_procesado


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
