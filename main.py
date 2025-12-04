import os
import io
import re
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from llama_parse import LlamaParse
from pypdf import PdfReader, PdfWriter

load_dotenv()

LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
if not LLAMA_CLOUD_API_KEY:
    raise ValueError("❌ Error: No se encontró la variable de entorno LLAMA_CLOUD_API_KEY")



URL_FIC = "https://www.bancolombia.com/wcm/connect/b6ff8232-01bc-4c48-ab13-64478693f86d/Informe+Rentabilidades+FIC.pdf?MOD=AJPERES"
JSON_STATUS_FILE = "data/processed_files.json"
PATRON_FECHA = r"Fecha de publicación:\s*(\d{1,2})\s+de\s+([a-zA-Z]+)\s+de\s+(\d{4})"

MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
}

now = datetime.now()
target_folder = f"data/raw_pdf/{now.strftime('%Y')}/{now.strftime('%m')}"
os.makedirs(target_folder, exist_ok=True)

parser = LlamaParse(
    api_key=LLAMA_CLOUD_API_KEY,
    result_type="markdown",
    verbose=False,
    language="es"
)

def cargar_historial_procesado():
    """Carga el JSON de fechas procesadas. Si no existe o falla, devuelve dict vacío."""
    if os.path.exists(JSON_STATUS_FILE):
        try:
            with open(JSON_STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {} # Archivo corrupto o vacío
    return {}

def guardar_historial_procesado(historial):
    """Guarda el diccionario actualizado en el JSON."""
    with open(JSON_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=4)

try:
    print("⬇️ Descargando PDF...")
    response = requests.get(URL_FIC, timeout=60)
    
    if response.status_code == 200:
        # 1. Procesamiento en Memoria
        archivo_memoria = io.BytesIO(response.content)
        reader = PdfReader(archivo_memoria)
        writer = PdfWriter()

        if len(reader.pages) > 0:
            writer.add_page(reader.pages[0])
            pdf_hoja_1_memoria = io.BytesIO()
            writer.write(pdf_hoja_1_memoria)
            pdf_hoja_1_memoria.seek(0)

            # 2. Extracción con LlamaParse
            print("🤖 Analizando con LlamaParse...")
            documents = parser.load_data(
                pdf_hoja_1_memoria, 
                extra_info={"file_name": "temp.pdf"}
            )
            
            mk_hoja_01 = documents[0].text
            match = re.search(PATRON_FECHA, mk_hoja_01, re.IGNORECASE)

            if match:
                dia, mes, anio = match.groups()
                mes_numero = MESES.get(mes.lower())
                
                if not mes_numero:
                    raise ValueError(f"Mes desconocido: {mes}")

                fecha_formateada = f"{anio}{mes_numero}{dia.zfill(2)}"
                print(f"📅 Fecha detectada en documento: {fecha_formateada}")

                # 3. Verificación de Idempotencia
                fechas_procesadas = cargar_historial_procesado()

                if fecha_formateada in fechas_procesadas:
                    print(f"⏭️ El archivo del {fecha_formateada} YA fue procesado anteriormente. Se omite descarga.")
                else:
                    # 4. Guardado (Solo si es nuevo)
                    timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')
                    # Opcional: Usar la fecha del documento en el nombre del archivo
                    filename = f"{target_folder}/rentabilidades_fic_{fecha_formateada}_downloaded_{timestamp}.pdf"
                    
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ Nuevo archivo guardado: {filename}")

                    # 5. ACTUALIZAR EL JSON (¡Esto faltaba!)
                    fechas_procesadas[fecha_formateada] = {
                        "downloaded_at": timestamp,
                        "path": filename
                    }
                    guardar_historial_procesado(fechas_procesadas)

            else:
                print("⚠️ No se encontró el patrón de fecha en el PDF. Revisa el Regex.")
        else:
            print("⚠️ El PDF descargado está vacío.")
    else:
        print(f"⚠️ Error HTTP {response.status_code}")
        
except Exception as e:
    print(f"❌ Error crítico: {e}")


# - Guardar JSON actualizado
with open(JSON_STATUS_FILE, "w", encoding="utf-8") as f:
    json.dump(fechas_procesadas, f, indent=4, ensure_ascii=False)

print("\n✅ Proceso completado correctamente.")