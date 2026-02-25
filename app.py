from flask import Flask, jsonify, request, render_template  # <--- 1. AÑADIDO render_template
import requests
import mysql.connector
from db import conectar_bd

app = Flask(__name__)

# --- RUTAS (ENDPOINTS) ---

@app.route('/')
def home():
    # <--- 2. CAMBIO IMPORTANTE: Ahora cargamos el HTML visual
    return render_template('index.html')

# --- LÓGICA DE NEGOCIO (Igual que antes) ---

def buscar_en_bd(termino):
    conn = conectar_bd()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM Libros WHERE titulo LIKE %s OR autor LIKE %s"
        patron = f"%{termino}%"
        cursor.execute(sql, (patron, patron))
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()

        libros_locales = []
        for row in resultados:
            libros_locales.append({
                'google_id': row['google_id'],
                'titulo': row['titulo'],
                'autor': row['autor'],
                'fecha': row['fecha_publicacion'],
                'descripcion': row['descripcion'],
                'portada': row['portada_url'],
                'origen': '🏠 LOCAL (MySQL)'
            })
        return libros_locales
    except Exception as e:
        print(f"Error BD: {e}")
        return []

def buscar_en_google(termino_busqueda):
    url = "https://www.googleapis.com/books/v1/volumes"
    parametros = {'q': termino_busqueda, 'langRestrict': 'es', 'maxResults': 40, 'printType': 'books'}
    try:
        respuesta = requests.get(url, params=parametros)
        if respuesta.status_code != 200: return []
        datos = respuesta.json()
        libros_limpios = []
        if 'items' in datos:
            for item in datos['items']:
                info = item.get('volumeInfo', {})
                libros_limpios.append({
                    'google_id': item.get('id'),
                    'titulo': info.get('title', 'Sin título'),
                    'autor': info.get('authors', ['Desconocido'])[0],
                    'fecha': info.get('publishedDate', 'S/F'),
                    'descripcion': info.get('description', 'Sin descripción'),
                    'portada': info.get('imageLinks', {}).get('thumbnail', None),
                    'origen': '🌍 INTERNET (Google)'
                })
        return libros_limpios
    except Exception as e:
        print(f"Error Google: {e}")
        return []

def guardar_libro_en_bd(datos_libro):
    conn = conectar_bd()
    if not conn: return {'error': 'Sin conexión BD'}

    try:
        cursor = conn.cursor()
        sql = """
            INSERT IGNORE INTO Libros 
            (google_id, titulo, autor, fecha_publicacion, descripcion, portada_url) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        valores = (
            datos_libro.get('google_id'),
            datos_libro.get('titulo'),
            datos_libro.get('autor'),
            datos_libro.get('fecha'),
            datos_libro.get('descripcion'),
            datos_libro.get('portada')
        )
        cursor.execute(sql, valores)
        conn.commit()
        filas = cursor.rowcount
        cursor.close()
        conn.close()

        if filas > 0:
            return {'mensaje': 'Libro guardado correctamente', 'status': 'success'}
        else:
            return {'mensaje': 'El libro ya existía', 'status': 'exists'}
    except Exception as e:
        print(f"Error guardando: {e}")
        return {'error': str(e), 'status': 'error'}

# --- RUTAS DE API (Igual que antes) ---

@app.route('/api/buscar', methods=['GET'])
def ruta_buscar():
    query = request.args.get('q')
    if not query: return jsonify({'error': 'Falta q'}), 400

    resultados = buscar_en_bd(query)
    if not resultados:
        resultados = buscar_en_google(query)

    return jsonify(resultados)

@app.route('/api/guardar-libro', methods=['POST'])
def ruta_guardar():
    datos = request.json
    return jsonify(guardar_libro_en_bd(datos))

@app.route('/api/test-db')
def test_db():
    conn = conectar_bd()
    if conn:
        conn.close()
        return jsonify({"estado": "online"})
    return jsonify({"estado": "offline"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)