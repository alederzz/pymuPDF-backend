from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import base64
import io
import os
from werkzeug.utils import secure_filename
import tempfile
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
        # Verificar si hay archivo en la petición
        if 'file' not in request.files:
            # Intentar obtener archivo como base64
            data = request.get_json()
            if data and 'pdf_base64' in data:
                pdf_data = base64.b64decode(data['pdf_base64'])
                password = data.get('password') if data else None
                doc = fitz.open(stream=pdf_data, filetype="pdf")
                if doc.needs_pass:
                    if not password or not doc.authenticate(password):
                        return jsonify({"error": "PDF is password-protected and password is missing or incorrect"}), 401
            else:
                return jsonify({"error": "No PDF file provided"}), 400
        else:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400

            if not allowed_file(file.filename):
                return jsonify({"error": "Invalid file type. Only PDF allowed"}), 400

            # Leer archivo directamente en memoria
            pdf_data = file.read()
            password = request.form.get('password')
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            if doc.needs_pass:
                if not password or not doc.authenticate(password):
                    return jsonify({"error": "PDF is password-protected and password is missing or incorrect"}), 401

        # Extraer texto de todas las páginas
        text_content = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()
            text_content.append({
                "page": page_num + 1,
                "text": text.strip()
            })

        doc.close()

        # Preparar respuesta
        response = {
            "success": True,
            "pages": len(text_content),
            "content": text_content,
            "full_text": "\n\n".join([page["text"] for page in text_content])
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
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
                password = data.get('password') if data else None
                doc = fitz.open(stream=pdf_data, filetype="pdf")
                if doc.needs_pass:
                    if not password or not doc.authenticate(password):
                        return jsonify({"error": "PDF is password-protected and password is missing or incorrect"}), 401
            else:
                return jsonify({"error": "No PDF file provided"}), 400
        else:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400

            if not allowed_file(file.filename):
                return jsonify({"error": "Invalid file type. Only PDF allowed"}), 400

            pdf_data = file.read()
            password = request.form.get('password')
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            if doc.needs_pass:
                if not password or not doc.authenticate(password):
                    return jsonify({"error": "PDF is password-protected and password is missing or incorrect"}), 401

        images = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)

                if pix.n - pix.alpha < 4:  # Solo RGB o escala de grises
                    img_data = pix.tobytes("png")
                    img_base64 = base64.b64encode(img_data).decode()

                    images.append({
                        "page": page_num + 1,
                        "image_index": img_index,
                        "format": "png",
                        "base64": img_base64
                    })

                pix = None

        doc.close()

        response = {
            "success": True,
            "images_found": len(images),
            "images": images
        }

        return jsonify(response)

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
                password = data.get('password') if data else None
                doc = fitz.open(stream=pdf_data, filetype="pdf")
                if doc.needs_pass:
                    if not password or not doc.authenticate(password):
                        return jsonify({"error": "PDF is password-protected and password is missing or incorrect"}), 401
            else:
                return jsonify({"error": "No PDF file provided"}), 400
        else:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400

            if not allowed_file(file.filename):
                return jsonify({"error": "Invalid file type. Only PDF allowed"}), 400

            pdf_data = file.read()
            password = request.form.get('password')
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            if doc.needs_pass:
                if not password or not doc.authenticate(password):
                    return jsonify({"error": "PDF is password-protected and password is missing or incorrect"}), 401

        # Obtener metadatos
        metadata = doc.metadata

        # Contar páginas e imágenes
        total_images = 0
        for page_num in range(doc.page_count):
            page = doc[page_num]
            total_images += len(page.get_images())

        doc.close()

        response = {
            "success": True,
            "info": {
                "pages": doc.page_count,
                "title": metadata.get('title', ''),
                "author": metadata.get('author', ''),
                "subject": metadata.get('subject', ''),
                "creator": metadata.get('creator', ''),
                "producer": metadata.get('producer', ''),
                "creation_date": metadata.get('creationDate', ''),
                "modification_date": metadata.get('modDate', ''),
                "total_images": total_images
            }
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error getting PDF info: {str(e)}")
        return jsonify({"error": f"Error getting PDF info: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)