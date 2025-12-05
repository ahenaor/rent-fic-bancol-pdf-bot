import time

import requests

from .config import BACKOFF_BASE, DOWNLOAD_TIMEOUT, MAX_RETRIES, logger


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
