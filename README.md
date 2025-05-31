# Backend PyMuPDF con Docker

Backend HTTP para procesar PDFs usando PyMuPDF, diseñado para integrarse con n8n mediante webhooks.

## Características

- 🔍 **Extracción de texto** de PDFs
- 🖼️ **Extracción de imágenes** de PDFs
- 📋 **Información del PDF** (metadatos, páginas, etc.)
- 🐳 **Containerizado con Docker**
- 🔗 **Compatible con n8n webhooks**
- 📝 **Soporte para archivos y base64**
- ⚙️ **Completamente configurable con variables de entorno**

## Instalación y Uso

### 1. Configuración inicial

```bash
# Clonar el proyecto
git clone <tu-repo>
cd pymupdf-backend

# Copiar archivo de configuración
cp .env.example .env

# Editar configuración (opcional)
nano .env
```

### 2. Configuración con variables de entorno

Crea un archivo `.env` basado en `.env.example`:

```bash
# Puerto del host (el que usas para conectarte)
HOST_PORT=5001

# Puerto interno del contenedor
CONTAINER_PORT=5000

# Entorno de Flask
FLASK_ENV=production

# Tamaño máximo de archivo (16MB = 16777216 bytes)
MAX_CONTENT_LENGTH=16777216

# Nivel de logging
LOG_LEVEL=INFO

# Extensiones permitidas
ALLOWED_EXTENSIONS=pdf
```

### 3. Ejecutar el servicio

```bash
# Construir y ejecutar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Verificar funcionamiento
curl http://localhost:5001/health
```

## Variables de Entorno Disponibles

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `HOST_PORT` | Puerto del host para conectarse | `5001` |
| `CONTAINER_PORT` | Puerto interno del contenedor | `5000` |
| `FLASK_ENV` | Entorno de Flask | `production` |
| `MAX_CONTENT_LENGTH` | Tamaño máximo de archivo (bytes) | `16777216` (16MB) |
| `UPLOAD_FOLDER` | Directorio de uploads interno | `/tmp/uploads` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `ALLOWED_EXTENSIONS` | Extensiones permitidas | `pdf` |
| `HEALTH_CHECK_INTERVAL` | Intervalo de health check | `30s` |
| `HEALTH_CHECK_TIMEOUT` | Timeout de health check | `10s` |
| `HEALTH_CHECK_RETRIES` | Reintentos de health check | `3` |

## Configuraciones Comunes

### Desarrollo local
```bash
# .env para desarrollo
FLASK_ENV=development
LOG_LEVEL=DEBUG
HOST_PORT=5000
MAX_CONTENT_LENGTH=52428800  # 50MB
```

### Producción con más capacidad
```bash
# .env para producción
FLASK_ENV=production
LOG_LEVEL=WARNING
HOST_PORT=8080
MAX_CONTENT_LENGTH=104857600  # 100MB
HEALTH_CHECK_INTERVAL=60s
```

### Múltiples formatos (experimental)
```bash
# Permitir otros formatos además de PDF
ALLOWED_EXTENSIONS=pdf,docx,txt
```

## Endpoints Disponibles

### 1. Extraer Texto (`/webhook/extract-text`)

Extrae todo el texto del PDF, página por página.

**Ejemplo con archivo:**
```bash
curl -X POST \
  -F "file=@documento.pdf" \
  http://localhost:5001/webhook/extract-text
```

**Ejemplo con base64:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"pdf_base64": "JVBERi0xLjQKJe..."}' \
  http://localhost:5001/webhook/extract-text
```

**Respuesta:**
```json
{
  "success": true,
  "pages": 3,
  "content": [
    {
      "page": 1,
      "text": "Contenido de la página 1..."
    }
  ],
  "full_text": "Todo el texto concatenado..."
}
```

### 2. Extraer Imágenes (`/webhook/extract-images`)

Extrae todas las imágenes del PDF en formato base64.

**Ejemplo:**
```bash
curl -X POST \
  -F "file=@documento.pdf" \
  http://localhost:5001/webhook/extract-images
```

**Respuesta:**
```json
{
  "success": true,
  "images_found": 2,
  "images": [
    {
      "page": 1,
      "image_index": 0,
      "format": "png",
      "base64": "iVBORw0KGgoAAAANSUhEUgAA..."
    }
  ]
}
```

### 3. Información del PDF (`/webhook/pdf-info`)

Obtiene metadatos y información general del PDF.

**Ejemplo:**
```bash
curl -X POST \
  -F "file=@documento.pdf" \
  http://localhost:5001/webhook/pdf-info
```

**Respuesta:**
```json
{
  "success": true,
  "info": {
    "pages": 5,
    "title": "Mi Documento",
    "author": "Autor",
    "creation_date": "2024-01-01",
    "total_images": 3
  }
}
```

## Integración con n8n

### 1. Configurar Webhook en n8n

1. Añade un nodo **Webhook** en tu workflow
2. Configura la URL: `http://tu-servidor:5001/webhook/extract-text`
3. Método: `POST`
4. Tipo de respuesta: `JSON`

### 2. Ejemplo de workflow n8n

```
[Trigger] → [HTTP Request] → [Process Data]
```

**Configuración del nodo HTTP Request:**
- URL: `http://localhost:5001/webhook/extract-text`
- Método: POST
- Body: Binary (para archivos) o JSON (para base64)

### 3. Procesar archivos desde n8n

Si tienes un archivo en n8n:
```javascript
// En el nodo Function
return [
  {
    json: {},
    binary: {
      data: items[0].binary.data
    }
  }
];
```

## Configuración Avanzada

### Cambiar configuración sin reconstruir

```bash
# Detener servicio
docker-compose down

# Editar .env
nano .env

# Reiniciar con nueva configuración
docker-compose up -d
```

### Configuración de límites de memoria y CPU

```yaml
# Añadir al docker-compose.yml
services:
  pymupdf-backend:
    # ... configuración existente
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

### Personalización de logging avanzado

```bash
# En .env para logging detallado
LOG_LEVEL=DEBUG
FLASK_ENV=development

# Ver logs en tiempo real
docker-compose logs -f pymupdf-backend
```

## Solución de Problemas

### Error de memoria con PDFs grandes

```dockerfile
# Añadir al Dockerfile
ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=1
```

### Logs de debug

```bash
# Ver logs del contenedor
docker-compose logs -f pymupdf-backend
```

### Verificar salud del servicio

```bash
# Health check básico
curl http://localhost:5001/health

# Health check con configuración
curl -s http://localhost:5001/health | jq '.config'
```

### Problemas de configuración

```bash
# Ver configuración actual
docker-compose exec pymupdf-backend env | grep -E "(PORT|FLASK|MAX_|LOG_)"

# Verificar variables de entorno
docker-compose config
```

## Desarrollo Local

### Sin Docker

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python app.py
```

### Con Docker para desarrollo

```bash
# Modo desarrollo con variables de entorno
docker run -it --rm \
  -p 5001:5000 \
  -v $(pwd):/app \
  -e FLASK_ENV=development \
  -e LOG_LEVEL=DEBUG \
  -e MAX_CONTENT_LENGTH=52428800 \
  pymupdf-backend
```

## Seguridad

- El servicio solo acepta archivos PDF
- Los archivos se procesan en memoria
- No se almacenan archivos permanentemente
- Límites de tamaño configurables

## Límites Conocidos

- Tamaño máximo de archivo: 16MB (configurable)
- Formatos soportados: Solo PDF
- Las imágenes se extraen como PNG
- No soporta PDFs con contraseña