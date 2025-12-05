# rent-fic-bancol-pdf-bot

Bot automatizado para descargar y procesar diariamente el informe de rentabilidades de Fondos de Inversión Colectiva (FIC) de Bancolombia.

## 📋 Descripción

Este proyecto descarga automáticamente el PDF de rentabilidades FIC publicado por Bancolombia, extrae la fecha de publicación del documento usando LlamaParse, y almacena el archivo de forma organizada por año y mes. Implementa un sistema de idempotencia para evitar descargas duplicadas.

## 🚀 Características

- **Descarga automática**: Obtiene el PDF más reciente desde la URL oficial de Bancolombia
- **Extracción inteligente**: Usa LlamaParse para extraer la fecha de publicación del documento
- **Organización por fecha**: Almacena los PDFs en estructura `data/raw_pdf/YYYY/MM/`
- **Idempotencia**: Evita procesar el mismo documento múltiples veces mediante un historial JSON
- **Reintentos automáticos**: Sistema de reintentos con backoff exponencial para descargas
- **Logging profesional**: Sistema de logs con timestamps y niveles apropiados
- **Protección de datos**: Backup automático del historial en caso de corrupción del JSON
- **Type hints completos**: Código con anotaciones de tipo para mejor mantenibilidad
- **Configuración centralizada**: Archivo YAML para gestionar todos los parámetros configurables

## 📁 Estructura del Proyecto

```
rent-fic-bancol-pdf-bot/
├── main.py                          # Script principal con type hints
├── config.yaml                      # Configuración centralizada
├── requirements.txt                 # Dependencias Python
├── .env                            # Variables de entorno (no versionado)
├── data/
│   ├── processed_files.json        # Historial de archivos procesados
│   ├── processed_files.json.bak    # Backup automático en caso de corrupción
│   ├── debug_last_markdown.txt     # Último markdown extraído (debug)
│   └── raw_pdf/
│       └── YYYY/
│           └── MM/
│               └── rentabilidades_fic_YYYYMMDD_downloaded_timestamp.pdf
└── .github/
    └── workflows/                  # GitHub Actions (opcional)
```

## 🛠️ Instalación

### Requisitos Previos

- **Python 3.10 o superior** (requerido para soporte de type hints modernos con sintaxis `|` para Union types)
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar el repositorio**:
```bash
git clone https://github.com/ahenaor/rent-fic-bancol-pdf-bot.git
cd rent-fic-bancol-pdf-bot
```

2. **Crear entorno virtual** (recomendado):
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**:
Crear un archivo `.env` en la raíz del proyecto:
```env
LLAMA_CLOUD_API_KEY=tu_api_key_aqui
```

Para obtener tu API key de LlamaParse, visita: https://cloud.llamaindex.ai/

5. **Configurar parámetros** (opcional):
El archivo [`config.yaml`](config.yaml) contiene todos los parámetros configurables del proyecto. Puedes modificarlo según tus necesidades (ver sección de Configuración más abajo).

**Nota sobre CONFIG_PATH**: Si necesitas usar un archivo de configuración en una ubicación diferente, puedes definir la variable de entorno `CONFIG_PATH`:
```bash
export CONFIG_PATH=/ruta/a/tu/config.yaml
python main.py
```

## 🎯 Uso

### Ejecución manual

```bash
python main.py
```

### Ejecución automática con GitHub Actions

El proyecto está preparado para ejecutarse automáticamente mediante GitHub Actions. Configura el secret `LLAMA_CLOUD_API_KEY` en tu repositorio.

## ⚙️ Configuración

El proyecto utiliza un archivo [`config.yaml`](config.yaml) para centralizar todos los parámetros configurables. Esto facilita el mantenimiento y permite ajustar el comportamiento sin modificar el código.

### Parámetros Configurables

#### Descarga (`download`)
- **`url`**: URL del PDF de Bancolombia
- **`timeout`**: Tiempo de espera para la descarga (segundos)
- **`max_retries`**: Número máximo de reintentos en caso de fallo
- **`backoff_base`**: Tiempo base para backoff exponencial (5 → 5s, 10s, 20s...)

#### Rutas (`paths`)
- **`json_status_file`**: Ruta del archivo JSON con historial de procesados
- **`debug_file`**: Ruta del archivo de debug con último markdown extraído
- **`raw_pdf_base`**: Directorio base para almacenar PDFs descargados

#### Patrones de Fecha (`date_patterns`)
- **`primary`**: Patrón regex principal para extraer la fecha
- **`fallback`**: Patrón regex de respaldo si el principal falla

#### Logging (`logging`)
- **`level`**: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **`format`**: Formato de los mensajes de log

#### LlamaParse (`llama_parse`)
- **`result_type`**: Tipo de resultado ("markdown", "text", etc.)
- **`verbose`**: Modo verbose para debugging
- **`language`**: Idioma del documento ("es" para español)

#### Meses (`months`)
- Mapeo de nombres de meses en español a números (01-12)

### Ejemplo de Configuración Personalizada

```yaml
download:
  max_retries: 5  # Aumentar reintentos
  backoff_base: 10  # Backoff más largo: 10s, 20s, 40s...

logging:
  level: "DEBUG"  # Más detalle en logs

paths:
  raw_pdf_base: "archivos/pdfs"  # Cambiar directorio de salida
```

## 🔧 Funcionamiento Técnico

### Flujo de Procesamiento

1. **Descarga**: Obtiene el PDF desde la URL de Bancolombia con reintentos automáticos
2. **Extracción de primera página**: Usa PyPDF para extraer solo la primera página (contiene la fecha)
3. **Parsing con LlamaParse**: Convierte el PDF a Markdown y extrae la fecha de publicación
4. **Validación de idempotencia**: Verifica si el documento ya fue procesado anteriormente
5. **Almacenamiento**: Guarda el PDF completo en la estructura de carpetas organizada por fecha
6. **Actualización de historial**: Registra el documento procesado en `processed_files.json`

### Sistema de Idempotencia

El archivo `data/processed_files.json` mantiene un registro de todas las fechas procesadas:

```json
{
    "20251201": {
        "downloaded_at": "2025-12-01_09-30-00",
        "path": "data/raw_pdf/2025/12/rentabilidades_fic_20251201_downloaded_2025-12-01_09-30-00.pdf"
    }
}
```

Si el archivo JSON se corrompe, automáticamente se crea un backup (`.bak`) y se inicia con un historial limpio.

### Patrones de Fecha

El sistema busca la fecha en el documento usando dos patrones regex:

- **Principal**: `Fecha de publicación: DD de MES de YYYY`
- **Respaldo**: `Fecha de publicación DD de MES de YYYY` con o sin dos puntos y tolerante a espacios

## 📊 Logging

El sistema utiliza el módulo `logging` de Python con el siguiente formato:

```
2025-12-05 09:30:00 [INFO] Descargando PDF...
2025-12-05 09:30:05 [INFO] Analizando con LlamaParse...
2025-12-05 09:30:10 [INFO] Fecha detectada en documento: 20251205
2025-12-05 09:30:11 [INFO] Nuevo archivo guardado: data/raw_pdf/2025/12/...
```

Niveles de log (configurables en [`config.yaml`](config.yaml)):
- `DEBUG`: Información detallada para debugging
- `INFO`: Operaciones normales (por defecto)
- `WARNING`: Situaciones que requieren atención pero no detienen el proceso
- `ERROR`: Errores críticos con stack trace completo
- `CRITICAL`: Errores críticos que impiden la ejecución

## 🔒 Seguridad

- Las credenciales se manejan mediante variables de entorno (`.env`)
- El archivo `.env` está excluido del control de versiones
- No se exponen API keys en el código

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🔗 Enlaces Útiles

- [Bancolombia - Rentabilidades FIC](https://www.bancolombia.com/personas/productos-servicios/inversiones/fondos-inversion-colectiva/rentabilidades)
- [LlamaParse Documentation](https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse/)
- [PyPDF Documentation](https://pypdf.readthedocs.io/)

## 🔍 Mejoras Técnicas

### Type Hints
El código incluye anotaciones de tipo completas en todas las funciones:
- Parámetros tipados: `def descargar_pdf(url: str, timeout: int) -> bytes`
- Retornos tipados: `-> Dict[str, Any]`, `-> None`, `-> bool`
- Tipos complejos: `tuple[str, str, str] | None` para valores opcionales

Esto mejora:
- **Autocompletado** en IDEs modernos
- **Detección temprana de errores** con herramientas como mypy
- **Documentación implícita** del código
- **Mantenibilidad** a largo plazo

### Arquitectura Modular
El código está organizado en funciones especializadas:
- `load_config()`: Carga configuración desde YAML con fallback y validación robusta
- `cargar_historial_procesado()`: Gestión del historial JSON con backup automático
- `descargar_pdf()`: Descarga con reintentos y backoff exponencial
- `extraer_primera_pagina()`: Extracción de página específica del PDF
- `extraer_fecha_documento()`: Parsing de fecha con regex (patrón principal + fallback)
- `formatear_fecha()`: Formateo de fecha a YYYYMMDD
- `guardar_debug_markdown()`: Guardado de markdown para debugging
- `procesar_pdf()`: Orquestación del procesamiento completo con validaciones defensivas
- `main()`: Función principal con manejo robusto de errores

### Validaciones Defensivas
El código incluye múltiples capas de validación:
- **Config loading**: Verifica existencia del archivo, parseo correcto, y contenido no vacío
- **LlamaParse response**: Valida que la API devuelva documentos y que contengan texto
- **PDF content**: Verifica que el PDF no esté vacío antes de procesarlo
- **Date extraction**: Intenta múltiples patrones regex antes de fallar
- **File operations**: Manejo de errores con backups automáticos

## ⚠️ Disclaimer

Este proyecto es un side project personal y no está afiliado oficialmente con Bancolombia. Los datos se obtienen de fuentes públicas disponibles en el sitio web de Bancolombia.
