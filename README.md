# Backend PyMuPDF con Docker

Backend HTTP para procesar PDFs usando PyMuPDF, diseñado para integrarse con n8n mediante webhooks.

## Características

- 🔍 **Extracción de texto** de PDFs
- 🖼️ **Extracción de imágenes** de PDFs
- 📋 **Información del PDF** (metadatos, páginas, etc.)
- 🐳 **Containerizado con Docker**
- 🔗 **Compatible con n8n webhooks**
- 📝 **Soporte para archivos y base64**

## Instalación y Uso

### 1. Clonar y construir

```bash
# Clonar el proyecto
git clone <tu-repo>
cd pymupdf-backend

# Construir y ejecutar con Docker Compose
docker-compose up -d
```

### 2. Verificar funcionamiento

```bash
# Health check
curl http://localhost:5000/health
```

## Endpoints Disponibles

### 1. Extraer Texto (`/webhook/extract-text`)

Extrae todo el texto del PDF, página por página.

**Ejemplo con archivo:**
```bash
curl -X POST \
  -F "file=@documento.pdf" \
  http://localhost:5000/webhook/extract-text
```

**Ejemplo con base64:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"pdf_base64": "JVBERi0xLjQKJe..."}' \
  http://localhost:5000/webhook/extract-text
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
  http://localhost:5000/webhook/extract-images
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
  http://localhost:5000/webhook/pdf-info
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
2. Configura la URL: `http://tu-servidor:5000/webhook/extract-text`
3. Método: `POST`
4. Tipo de respuesta: `JSON`

### 2. Ejemplo de workflow n8n

```
[Trigger] → [HTTP Request] → [Process Data]
```

**Configuración del nodo HTTP Request:**
- URL: `http://localhost:5000/webhook/extract-text`
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

### Variables de entorno

```yaml
environment:
  - PORT=5000
  - FLASK_ENV=production
  - MAX_CONTENT_LENGTH=16777216  # 16MB
```

### Personalización de límites

Edita `app.py` para cambiar límites:

```python
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
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
curl http://localhost:5000/health
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
# Modo desarrollo con auto-reload
docker run -it --rm \
  -p 5000:5000 \
  -v $(pwd):/app \
  -e FLASK_ENV=development \
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