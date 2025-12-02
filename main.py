import os
import requests
from datetime import datetime

# URL constante
URL_FIC = "https://www.bancolombia.com/wcm/connect/b6ff8232-01bc-4c48-ab13-64478693f86d/Informe+Rentabilidades+FIC.pdf?MOD=AJPERES"

# 1. Configurar carpetas: data/2025/12
now = datetime.now()
target_folder = f"data/{now.strftime('%Y')}/{now.strftime('%m')}"

if not os.path.exists(target_folder):
    os.makedirs(target_folder)

# 2. Descargar y Guardar
try:
    print(f"Iniciando descarga desde Bancolombia...")
    
    # Timeout de 30s es prudente para la web del banco
    response = requests.get(URL_FIC, timeout=30)
    
    if response.status_code == 200:
        # Generamos nombre: rentabilidades_fic_2025-12-02.pdf
        # Usamos solo fecha (sin hora) si el archivo solo cambia una vez al día, 
        # pero mantenemos hora si quieres ejecutarlo varias veces para probar.
        timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"{target_folder}/rentabilidades_fic_{timestamp}.pdf"
        
        with open(filename, 'wb') as f:
            f.write(response.content)
            
        print(f"✅ Éxito! Guardado en: {filename}")
        
    else:
        print(f"⚠️ Error HTTP {response.status_code} al intentar descargar.")
        
except Exception as e:
    print(f"❌ Error crítico de ejecución: {e}")