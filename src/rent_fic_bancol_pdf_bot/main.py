import os

from dotenv import load_dotenv
from llama_parse import LlamaParse

from .config import CONFIG, URL_FIC, logger
from .download import descargar_pdf
from .history import cargar_historial_procesado
from .pdf_processor import procesar_pdf


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
