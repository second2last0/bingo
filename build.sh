#!/usr/bin/env bash

# Actualizar paquetes e instalar Tesseract
apt-get update && apt-get install -y tesseract-ocr

# Verificar la instalación
which tesseract
tesseract --version

# Añadir la ruta de Tesseract al PATH si no está ya configurada
export PATH=$PATH:/usr/bin

