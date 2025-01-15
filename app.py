from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import re
import io
import platform
import os

app = Flask(__name__)


import subprocess

try:
    result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, check=True)
    print("Tesseract está instalado:")
    print(result.stdout)
except FileNotFoundError:
    print("Tesseract no está instalado o no está en PATH.")


# Configurar pytesseract dependiendo del sistema operativo
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:  # Linux o Android
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def leer_pdf(ruta_archivo):
    texto_completo = []
    try:
        with fitz.open(ruta_archivo) as doc:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Extraer texto de la página
                text = page.get_text()
                if text:
                    texto_completo.append(text)
                # Procesar imágenes de la página
                for img in page.get_images(full=True):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_data = base_image["image"]
                    img = Image.open(io.BytesIO(image_data))
                    img = img.resize((800, 800)).convert('L')  # Optimización
                    texto_completo.append(pytesseract.image_to_string(img))
    except Exception as e:
        print(f"Error procesando {ruta_archivo}: {e}")
    return "\n".join(texto_completo)



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

@app.route('/')
def home():
    return "Hello, Flask is running!"



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


from concurrent.futures import ThreadPoolExecutor
import tempfile

def procesar_un_pdf(archivo):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            archivo.save(temp_file.name)
            texto = leer_pdf(temp_file.name)
            tablas = extraer_tablas(texto)
        os.remove(temp_file.name)

        return {
            "archivo": archivo.filename,
            "tablas": [
                {
                    "codigo": tabla["codigo"],
                    "numeros_ordenados": reordenar_numeros(
                        [num for fila in tabla["numeros"] for num in fila][:24]
                    )
                }
                for tabla in tablas
            ]
        }
    except Exception as e:
        return {"archivo": archivo.filename, "error": str(e)}

@app.route('/procesar_pdf_files', methods=['POST'])
def procesar_pdf_files():
    if 'files' not in request.files:
        return jsonify({"error": "No se encontraron archivos en la solicitud"}), 400

    archivos = request.files.getlist('files')
    with ThreadPoolExecutor() as executor:
        resultados = list(executor.map(procesar_un_pdf, archivos))

    return jsonify({"resultados": resultados})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

