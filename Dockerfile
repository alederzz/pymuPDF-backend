# Usar imagen base de Python 3.13 slim
FROM python:3.13-slim

# Instalar dependencias del sistema necesarias para PyMuPDF
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libmupdf-dev \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements.txt
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY app.py .
COPY gunicorn.conf.py .

# Crear directorio para archivos temporales
RUN mkdir -p /tmp/uploads

# Exponer puerto
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["sh", "-c", "if [ \"$FLASK_ENV\" = \"development\" ]; then python app.py; else gunicorn -c gunicorn.conf.py app:app; fi"]