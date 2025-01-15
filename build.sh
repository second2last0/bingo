#!/usr/bin/env bash

# Actualizar paquetes
apt-get update && apt-get install -y tesseract-ocr

# Verificar instalación de Tesseract
tesseract --version
