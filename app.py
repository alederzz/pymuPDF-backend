from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import base64
import os
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)

# Configuración desde variables de entorno
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16777216))  # 16MB por defecto
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'pdf').split(','))

# Configurar Flask
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Crear directorio de uploads si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    return jsonify({
        "status": "healthy",
        "service": "pymupdf-backend",
        "config": {
            "max_content_length": MAX_CONTENT_LENGTH,
            "allowed_extensions": list(ALLOWED_EXTENSIONS),
            "upload_folder": UPLOAD_FOLDER,
            "log_level": LOG_LEVEL
        }
    })

@app.route('/webhook/extract-text', methods=['POST'])
def extract_text_webhook():
    """Extrae texto de un PDF mediante webhook"""
    try:
        logger.debug("Inicio de extracción de texto")
        pdf_data = None
        password = None
        source = "unknown"

        # Verificar si hay archivo en la petición (multipart)
        if 'file' in request.files:
            logger.debug("PDF recibido como archivo binario (multipart/form-data)")
            file = request.files['file']
            if file.filename == '':
                logger.warning("Archivo recibido pero sin nombre")
                return jsonify({"error": "Archivo sin nombre"}), 400
            if not allowed_file(file.filename):
                logger.warning(f"Extensión no permitida: {file.filename}")
                return jsonify({"error": "Tipo de archivo no permitido"}), 400
            pdf_data = file.read()
            password = request.form.get('password')
            source = "multipart"
        else:
            # Intentar obtener base64 desde JSON
            logger.debug("No se encontró archivo, intentando cargar JSON")
            data = request.get_json()
            if data:
                if 'pdf_base64' in data:
                    pdf_data = base64.b64decode(data['pdf_base64'])
                    source = "base64"
                    logger.debug("PDF recibido como base64")
                else:
                    logger.warning("Campo 'pdf_base64' no encontrado en JSON")
                password = data.get('password')
            else:
                logger.warning("No se pudo cargar JSON desde la solicitud")
                return jsonify({"error": "No PDF file provided"}), 400

        # Verificar contenido del archivo
        if not pdf_data or len(pdf_data) < 100:
            logger.error("El PDF está vacío o corrupto")
            return jsonify({"error": "PDF está vacío o inválido"}), 400

        logger.info(f"PDF recibido correctamente desde: {source}")
        logger.debug(f"Tamaño del PDF: {len(pdf_data)} bytes")
        logger.debug(f"Contraseña recibida: {'sí' if password else 'no'}")

        # Guardar PDF para depuración (opcional)
        debug_path = os.path.join(UPLOAD_FOLDER, f"debug_{source}.pdf")
        with open(debug_path, "wb") as f:
            f.write(pdf_data)
        logger.debug(f"PDF guardado temporalmente en {debug_path}")

        # Abrir PDF
        doc, error = open_pdf_with_auth(pdf_data, password)
        if error:
            logger.warning(f"No se pudo abrir el PDF: {error}")
            return jsonify({"error": error}), 401

        # Extraer texto
        text_content = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text()
            text_content.append({
                "page": page_num + 1,
                "text": text.strip()
            })

        doc.close()

        return jsonify({
            "success": True,
            "pages": len(text_content),
            "content": text_content,
            "full_text": "\n\n".join([page["text"] for page in text_content])
        })

    except Exception as e:
        logger.error(f"Error general al procesar PDF: {str(e)}", exc_info=True)
        return jsonify({"error": f"Error processing PDF: {str(e)}"}), 500

@app.route('/webhook/extract-images', methods=['POST'])
def extract_images_webhook():
    """Extrae imágenes de un PDF mediante webhook"""
    try:
        # Verificar si hay archivo en la petición
        if 'file' not in request.files:
            data = request.get_json()
            if data and 'pdf_base64' in data:
                pdf_data = base64.b64decode(data['pdf_base64'])
                password = data.get('password')
            else:
                return jsonify({"error": "No PDF file provided"}), 400
        else:
            file = request.files['file']
            if file.filename == '' or not allowed_file(file.filename):
                return jsonify({"error": "Invalid or missing PDF file"}), 400
            pdf_data = file.read()
            password = request.form.get('password')

        doc, error = open_pdf_with_auth(pdf_data, password)
        if error:
            return jsonify({"error": error}), 401

        images = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            for img_index, img in enumerate(page.get_images()):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha < 4:
                    img_data = pix.tobytes("png")
                    img_base64 = base64.b64encode(img_data).decode()
                    images.append({
                        "page": page_num + 1,
                        "image_index": img_index,
                        "format": "png",
                        "base64": img_base64
                    })

        doc.close()

        return jsonify({
            "success": True,
            "images_found": len(images),
            "images": images
        })

    except Exception as e:
        logger.error(f"Error extracting images: {str(e)}")
        return jsonify({"error": f"Error extracting images: {str(e)}"}), 500

@app.route('/webhook/pdf-info', methods=['POST'])
def pdf_info_webhook():
    """Obtiene información general del PDF"""
    try:
        if 'file' not in request.files:
            data = request.get_json()
            if data and 'pdf_base64' in data:
                pdf_data = base64.b64decode(data['pdf_base64'])
                password = data.get('password')
            else:
                return jsonify({"error": "No PDF file provided"}), 400
        else:
            file = request.files['file']
            if file.filename == '' or not allowed_file(file.filename):
                return jsonify({"error": "Invalid or missing PDF file"}), 400
            pdf_data = file.read()
            password = request.form.get('password')

        doc, error = open_pdf_with_auth(pdf_data, password)
        if error:
            return jsonify({"error": error}), 401

        # Obtener metadatos
        metadata = doc.metadata
        total_images = sum(len(doc.load_page(p).get_images()) for p in range(doc.page_count))
        total_pages = doc.page_count

        doc.close()

        return jsonify({
            "success": True,
            "info": {
                "pages": total_pages,
                "title": metadata.get('title', ''),
                "author": metadata.get('author', ''),
                "subject": metadata.get('subject', ''),
                "creator": metadata.get('creator', ''),
                "producer": metadata.get('producer', ''),
                "creation_date": metadata.get('creationDate', ''),
                "modification_date": metadata.get('modDate', ''),
                "total_images": total_images
            }
        })

    except Exception as e:
        logger.error(f"Error getting PDF info: {str(e)}")
        return jsonify({"error": f"Error getting PDF info: {str(e)}"}), 500

def open_pdf_with_auth(pdf_data, password=None):
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
    except Exception as e:
        logger.error(f"No se pudo abrir el PDF: {str(e)}")
        return None, "Error abriendo el PDF"

    if doc.needs_pass:
        logger.debug("El PDF está protegido con contraseña")
        if not password:
            logger.warning("El PDF necesita contraseña pero no se proporcionó")
            return None, "PDF is password-protected and no password was provided"
        if not doc.authenticate(password):
            logger.warning("La contraseña proporcionada es incorrecta")
            return None, "Incorrect PDF password"

    if doc.page_count == 0:
        logger.warning("El PDF no tiene páginas válidas (page_count == 0)")
        return None, "PDF appears to be empty or corrupted"

    logger.debug("El PDF fue abierto exitosamente y contiene páginas")
    return doc, None

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)