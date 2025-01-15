FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y tesseract-ocr libtesseract-dev

# Configurar el directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY . .

# Instalar dependencias de Python
RUN pip install -r requirements.txt

# Comando para iniciar la aplicación
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
