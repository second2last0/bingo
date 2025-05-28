from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import re
import os
from concurrent.futures import ThreadPoolExecutor
import tempfile
from flask_cors import CORS


# Inicializar Flask
app = Flask(__name__)
CORS(app)

# Función para leer y procesar un PDF
def leer_pdf(ruta_archivo):
    texto_completo = []
    try:
        with fitz.open(ruta_archivo) as doc:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Extraer texto directamente
                text = page.get_text()
                if text:
                    texto_completo.append(text)
    except Exception as e:
        print(f"Error procesando {ruta_archivo}: {e}")
    return "\n".join(texto_completo)

# Función para extraer tablas del texto
def extraer_tablas(texto):
    lineas = texto.splitlines()
    tablas = []
    tabla_actual = []
    codigo_actual = None

    for i, linea in enumerate(lineas):
        linea = linea.strip()

        # --- FORMATO NUEVO ---
        if re.match(r'^[~‡]?\s*#\d{7}', linea):
            if tabla_actual and codigo_actual and not es_tabla_especial(codigo_actual):
                tablas.append({"codigo": codigo_actual, "numeros": tabla_actual})
            codigo_actual = re.sub(r'[^0-9]', '', linea)  # extraer solo los dígitos del código
            tabla_actual = []
            continue

        if re.match(r'^\d{1,2}$', linea):  # línea solo con un número
            tabla_actual.append([linea])
            continue

        # --- FORMATO ANTIGUO ---
        if "TABLA No." in linea or "TABLA #" in linea:
            if tabla_actual and codigo_actual and not es_tabla_especial(codigo_actual):
                tablas.append({"codigo": codigo_actual, "numeros": tabla_actual})
            if "TABLA No." in linea:
                codigo_actual = linea.split("TABLA No.")[-1].strip()
            elif "TABLA #" in linea:
                codigo_actual = linea.split("TABLA #")[-1].strip()
            tabla_actual = []
        else:
            numeros = re.findall(r'\b\d{1,2}\b', linea)
            if numeros:
                tabla_actual.append(numeros)

    # guardar última tabla
    if tabla_actual and codigo_actual and not es_tabla_especial(codigo_actual):
        tablas.append({"codigo": codigo_actual, "numeros": tabla_actual})

    return tablas

# Determinar si una tabla es especial
def es_tabla_especial(codigo):
    especiales = ["0077731", "0077732"]
    return codigo in especiales

# Reordenar números según una lógica específica
def reordenar_numeros(numeros_en_fila):
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

# Procesar un único PDF
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

# Ruta principal
@app.route('/')
def home():
    return "Hello, Flask is running!"

# Ruta para procesar PDFs
@app.route('/procesar_pdf_files', methods=['POST'])
def procesar_pdf_files():
    if 'files' not in request.files:
        return jsonify({"error": "No se encontraron archivos en la solicitud"}), 400

    archivos = request.files.getlist('files')
    with ThreadPoolExecutor() as executor:
        resultados = list(executor.map(procesar_un_pdf, archivos))

    print("RESULTADOS DEL SERVIDOR:")
    print(resultados)  # 👈 Esto mostrará en consola lo que el servidor va a enviar

    return jsonify({"resultados": resultados})

# Ruta de prueba
@app.route('/test_update', methods=['GET'])
def test_update():
    return "El servidor está actualizado correctamente.", 200

# Ejecutar servidor
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



