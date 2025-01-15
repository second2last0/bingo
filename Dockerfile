# Usa una imagen base con Python
FROM python:3.11-slim

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y \
    && apt-get clean

# Crea el directorio de la aplicación
WORKDIR /app

# Copia los archivos del proyecto
COPY requirements.txt ./
COPY app.py ./

# Instala dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto 5000
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]



