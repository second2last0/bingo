from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import re
import io
import platform
import os

app = Flask(__name__)

# Configurar pytesseract dependiendo del sistema operativo
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:  # Linux o Android
    pytesseract.pytesseract.tesseract_cmd = '/data/data/org.test.myapp/files/tesseract'

def leer_pdf(ruta_archivo):
    """Extraer texto y procesar imágenes de todas las páginas de un archivo PDF."""
    texto_completo = ""
    try:
        with fitz.open(ruta_archivo) as doc:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Extraer texto de la página
                text = page.get_text()
                if text:
                    texto_completo += text + "\n"  # Asegurar que las páginas estén separadas
                # Procesar imágenes de la página
                for img in page.get_images(full=True):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_data = base_image["image"]
                    img = Image.open(io.BytesIO(image_data))
                    texto_completo += pytesseract.image_to_string(img) + "\n"
    except Exception as e:
        print(f"Error procesando {ruta_archivo}: {e}")
    return texto_completo


def extraer_tablas(texto):
    """Extraer tablas del texto leído del PDF."""
    lineas = texto.splitlines()
    tablas = []
    tabla_actual = []
    codigo_actual = None

    for linea in lineas:
        if "TABLA No." in linea or "TABLA #" in linea:
            if tabla_actual and codigo_actual and not es_tabla_especial(codigo_actual):
                tablas.append({"codigo": codigo_actual, "numeros": tabla_actual})
                tabla_actual = []
                codigo_actual = None

            if "TABLA No." in linea:
                codigo_actual = linea.split("TABLA No.")[-1].strip()
            elif "TABLA #" in linea:
                codigo_actual = linea.split("TABLA #")[-1].strip()
        else:
            numeros = re.findall(r'\b\d{1,2}\b', linea)
            if numeros:
                tabla_actual.append(numeros)

    if tabla_actual and codigo_actual and not es_tabla_especial(codigo_actual):
        tablas.append({"codigo": codigo_actual, "numeros": tabla_actual})

    return tablas



@app.route('/test_pdf_pages', methods=['POST'])
def test_pdf_pages():
    """Probar si se reconocen todas las páginas de un archivo PDF."""
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró un archivo en la solicitud"}), 400

    archivo = request.files['file']
    if archivo.filename == '' or not archivo.filename.lower().endswith('.pdf'):
        return jsonify({"error": "El archivo no es un PDF o está vacío"}), 400

    try:
        # Guardar temporalmente el archivo
        ruta_temporal = f"temp_{archivo.filename}"
        archivo.save(ruta_temporal)

        # Procesar el archivo
        paginas_info = []
        with fitz.open(ruta_temporal) as doc:
            num_paginas = len(doc)
            for page_num in range(num_paginas):
                page = doc.load_page(page_num)
                texto = page.get_text()
                imagenes = page.get_images(full=True)

                # Obtener información de la página
                paginas_info.append({
                    "pagina": page_num + 1,
                    "texto": texto.strip() if texto else "No se encontró texto",
                    "num_imagenes": len(imagenes),
                })

        # Eliminar el archivo temporal
        os.remove(ruta_temporal)

        return jsonify({
            "total_paginas": len(paginas_info),
            "paginas": paginas_info
        })

    except Exception as e:
        return jsonify({"error": f"Error procesando el archivo: {e}"}), 500


def es_tabla_especial(codigo):
    """Determina si una tabla es especial y debe omitirse."""
    especiales = ["0077731", "0077732"]
    return codigo in especiales

def reordenar_numeros(numeros_en_fila):
    """Reorganizar números según una lógica específica."""
    try:
        numero_a_comparar = int(numeros_en_fila[20])
        if numero_a_comparar < 40:
            numeros_correctos = (
                numeros_en_fila[:6] +
                [numeros_en_fila[20]] +
                numeros_en_fila[6:7] +
                [numeros_en_fila[21]] +
                numeros_en_fila[7:13] +
                [numeros_en_fila[22]] +
                numeros_en_fila[13:14] +
                [numeros_en_fila[23]] +
                numeros_en_fila[14:20]
            )
        else:
            numeros_correctos = numeros_en_fila
    except (ValueError, IndexError) as e:
        print(f"Error al reordenar números: {e}")
        numeros_correctos = numeros_en_fila
    return numeros_correctos

@app.route('/test_update', methods=['GET'])
def test_update():
    return "El servidor está actualizado correctamente.", 200


@app.route('/procesar_pdf_files', methods=['POST'])
def procesar_pdf_files():
    """Procesar múltiples archivos PDF enviados en la solicitud."""
    if 'files' not in request.files:
        return jsonify({"error": "No se encontraron archivos en la solicitud"}), 400

    archivos = request.files.getlist('files')
    resultado = []

    for archivo in archivos:
        if archivo.filename == '' or not archivo.filename.lower().endswith('.pdf'):
            resultado.append({
                "archivo": archivo.filename,
                "error": "El archivo no es un PDF o está vacío"
            })
            continue

        try:
            # Guardar temporalmente el archivo
            ruta_temporal = f"temp_{archivo.filename}"
            archivo.save(ruta_temporal)

            # Leer el texto y extraer tablas
            texto = leer_pdf(ruta_temporal)
            tablas = extraer_tablas(texto)  # Procesar todas las páginas

            resultado_tablas = []
            for tabla in tablas:
                numeros = tabla["numeros"]
                numeros_en_fila = [num for fila in numeros for num in fila][:24]
                numeros_ordenados = reordenar_numeros(numeros_en_fila)
                try:
                    numeros_ordenados = [int(num) for num in numeros_ordenados]
                except ValueError:
                    pass
                resultado_tablas.append({
                    "codigo": tabla["codigo"],
                    "numeros_ordenados": numeros_ordenados
                })

            resultado.append({
                "archivo": archivo.filename,
                "tablas": resultado_tablas
            })

            # Eliminar el archivo temporal
            os.remove(ruta_temporal)

        except Exception as e:
            resultado.append({
                "archivo": archivo.filename,
                "error": str(e)
            })

    return jsonify({"resultados": resultado})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

