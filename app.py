import logging
import os
import random
import urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import mysql.connector
import requests
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from db import conectar_bd

# ==========================================
# CONFIGURACIÓN
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'super_secreta_bookradar_2026_clave_unica')


# ==========================================
# FUNCIONES AUXILIARES Y LÓGICA
# ==========================================

def fetch_books_category(query, order="relevance", max_results=10):
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {'q': query, 'orderBy': order, 'maxResults': max_results, 'langRestrict': 'es', 'printType': 'books'}
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            items = resp.json().get('items', [])
            return [{
                'google_id': item.get('id'),
                'titulo': item.get('volumeInfo', {}).get('title', 'Sin título'),
                'autor': ", ".join(item.get('volumeInfo', {}).get('authors', ['Desconocido'])),
                'portada': item.get('volumeInfo', {}).get('imageLinks', {}).get('thumbnail'),
                'puntuacion': item.get('volumeInfo', {}).get('averageRating', 0)
            } for item in items]
    except Exception as e:
        logging.error(f"Error cargando categoría {query}: {e}")
    return []


def guardar_libro_en_bd(datos_libro, user_id, estado):
    conn = conectar_bd()
    if not conn: return {'status': 'error', 'mensaje': 'Sin conexión'}

    try:
        cursor = conn.cursor(dictionary=True)
        google_id = datos_libro.get('google_id')

        cursor.execute("SELECT id_libros FROM libros WHERE google_id = %s", (google_id,))
        resultado = cursor.fetchone()

        if resultado:
            id_libro_db = resultado['id_libros']
        else:
            cats = datos_libro.get('categorias', 'General')
            cats_str = ", ".join(cats) if isinstance(cats, list) else str(cats)
            cats_str = cats_str[:100]

            sql_ins = """
                INSERT INTO libros (google_id, titulo, autor, categorias, fecha, portada_url, sinopsis) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_ins, (
                google_id,
                datos_libro.get('titulo', 'Sin título')[:150],
                datos_libro.get('autor', 'Desconocido')[:100],
                cats_str,
                datos_libro.get('fecha', 'S/F'), # <--- Coincide con la nueva columna
                datos_libro.get('portada') or datos_libro.get('portada_url', ''),
                datos_libro.get('sinopsis') or datos_libro.get('descripcion') or 'Sin descripción'
            ))
            id_libro_db = cursor.lastrowid

        calif = datos_libro.get('calificacion') or 0
        resena = datos_libro.get('resena') or datos_libro.get('comentario') or ''

        sql_rel = """
                  INSERT INTO usuarios_libros (id_usuario, id_libro, estado, calificacion, comentario)
                  VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY \
                  UPDATE \
                      estado = \
                  VALUES (estado), calificacion = IF(VALUES (calificacion) > 0, VALUES (calificacion), calificacion), comentario = IF(VALUES (comentario) != '', VALUES (comentario), comentario) \
                  """
        cursor.execute(sql_rel, (user_id, id_libro_db, estado, int(calif), resena))
        conn.commit()
        return {'status': 'success'}

    except Exception as e:
        if conn: conn.rollback()
        print(f"DEBUG ERROR: {e}")
        return {'status': 'error', 'mensaje': str(e)}
    finally:
        if conn: conn.close()


# ==========================================
# 1. RUTAS DE NAVEGACIÓN (Vistas HTML)
# ==========================================

@app.route('/')
def vista_inicio():
    # Si el usuario está logueado, verificamos su configuración
    if 'id_usuario' in session:
        uid = session['id_usuario']
        conn = conectar_bd()
        cursor = conn.cursor()

        # Contamos cuántos géneros tiene elegidos
        cursor.execute("SELECT COUNT(*) FROM preferencias_usuario WHERE id_usuario = %s", (uid,))
        conteo = cursor.fetchone()[0]
        conn.close()

        # Si tiene menos de 3 (o 0), le obligamos a ir al Paso 2
        if conteo < 3:
            return redirect(url_for('vista_registro_paso2'))

    # Si todo está OK o es un invitado, cargamos la página normal
    secciones_config = [
        {"id": "tendencias", "titulo": "Tendencias Globales", "query": "best sellers 2026", "order": "relevance"},
        {"id": "misterio", "titulo": "Misterio y Suspense", "query": "subject:Mystery", "order": "relevance"}
    ]
    secciones_datos = {}
    with ThreadPoolExecutor() as executor:
        futuros = {executor.submit(fetch_books_category, s["query"], s["order"]): s["id"] for s in secciones_config}
        for futuro in as_completed(futuros):
            cat_id = futuros[futuro]
            secciones_datos[cat_id] = futuro.result()


    return render_template('index.html', secciones=secciones_config, datos=secciones_datos)


@app.route('/registro', methods=['GET', 'POST'])
def vista_registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = generate_password_hash(request.form.get('password'))

        conn = conectar_bd()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO usuarios (nombre_usuario, email, contraseña) VALUES (%s, %s, %s)",
                           (nombre, email, password))
            uid = cursor.lastrowid
            conn.commit()

            # Iniciamos sesión automáticamente para que el sistema sepa quién es en el Paso 2
            session['id_usuario'] = uid
            session['nombre_usuario'] = nombre

            # REDIRIGIR AL PASO 2 (Selección de géneros)
            return redirect(url_for('vista_registro_paso2'))
        except Exception as e:
            return render_template('registro.html', error="El email ya existe.")
        finally:
            conn.close()
    return render_template('registro.html')


@app.route('/registro-paso2', methods=['GET', 'POST'])
def vista_registro_paso2():
    if 'id_usuario' not in session:
        return redirect(url_for('vista_login'))

    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        generos_seleccionados = request.form.getlist('generos')
        uid = session['id_usuario']

        # VALIDACIÓN: Forzamos mínimo 3 categorías
        if len(generos_seleccionados) < 3:
            cursor.execute("SELECT * FROM generos")
            return render_template('registro_paso2.html',
                                   generos=cursor.fetchall(),
                                   error="Por favor, selecciona al menos 3 categorías para continuar.")

        # Si pasa la validación, guardamos en la base de datos
        try:
            for gid in generos_seleccionados:
                cursor.execute("INSERT INTO preferencias_usuario (id_usuario, id_genero) VALUES (%s, %s)", (uid, gid))
            conn.commit()
            return redirect(url_for('vista_inicio')) # O a tu ruta de bienvenida
        except Exception as e:
            conn.rollback()
            return render_template('registro_paso2.html', error="Error al guardar preferencias.")
        finally:
            conn.close()

    cursor.execute("SELECT * FROM generos")
    todos_generos = cursor.fetchall()
    conn.close()
    return render_template('registro_paso2.html', generos=todos_generos)


@app.route('/login', methods=['GET', 'POST'])
def vista_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = conectar_bd()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_usuarios, nombre_usuario, contraseña FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()
        conn.close()

        if usuario and check_password_hash(usuario['contraseña'], password):
            # Login exitoso: Limpiamos sesión vieja y creamos la nueva
            session.clear()
            session['id_usuario'] = usuario['id_usuarios']
            session['nombre_usuario'] = usuario['nombre_usuario']

            # Redirigimos al inicio, que se encargará de verificar si tiene los 3 géneros
            return redirect(url_for('vista_inicio'))

        return render_template('login.html', error="Credenciales incorrectas")

    return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('vista_inicio'))

@app.route('/buscar')
def vista_buscar():
    query = request.args.get('q', '').strip()
    genero = request.args.get('genero', '')
    orden = request.args.get('orden', 'relevance')

    libros_resultado = []

    if query or genero:
        if query and genero:
            full_query = f"{query} + subject:{genero}"
        elif genero:
            full_query = f"subject:{genero}"
        else:
            full_query = query

        params = {
            'q': full_query,
            'orderBy': orden,
            'maxResults': 24,
            'langRestrict': 'es',
            'printType': 'books'
        }

        url = "https://www.googleapis.com/books/v1/volumes"

        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get('items', []):
                    vol = item.get('volumeInfo', {})
                    libros_resultado.append({
                        'google_id': item.get('id'),
                        'titulo': vol.get('title', 'Sin título'),
                        'autor': ", ".join(vol.get('authors', ['Desconocido'])),
                        'portada': vol.get('imageLinks', {}).get('thumbnail'),
                        'sinopsis': vol.get('description', ''),
                        'categorias': vol.get('categories', [])
                    })
        except Exception as e:
            print(f"Error en búsqueda: {e}")

    generos_lista = ["Ficción", "Misterio", "Terror", "Romance", "Ciencia Ficción", "Fantasía", "Historia", "Biografía", "Infantil", "Autoayuda"]

    return render_template('buscar.html',
                           libros=libros_resultado,
                           query=query,
                           genero_sel=genero,
                           orden_sel=orden,
                           generos=generos_lista)

@app.route('/mis-libros')
def vista_mis_libros():

    if 'id_usuario' not in session:
        return redirect(url_for('vista_login'))


    filtro_estado = request.args.get('estado')
    libros_guardados = []
    conn = conectar_bd()

    if conn:
        try:
            cursor = conn.cursor(dictionary=True)


            sql = """
                SELECT l.*, ul.estado FROM libros l
                JOIN usuarios_libros ul ON l.id_libros = ul.id_libro
                WHERE ul.id_usuario = %s
            """
            params = [session['id_usuario']]

            if filtro_estado in ['LEIDO', 'DESEADO', 'NO_INTERESA']:
                sql += " AND ul.estado = %s"
                params.append(filtro_estado)

            sql += " ORDER BY ul.fecha_guardado DESC"

            cursor.execute(sql, tuple(params))
            libros_guardados = cursor.fetchall()
        except Exception as e:
            logging.error(f"Fallo al cargar biblioteca: {e}")
        finally:
            conn.close()

    return render_template('mis_libros.html', libros=libros_guardados, filtro=filtro_estado)


# ==========================================
# 2. LÓGICA DE NEGOCIO
# ==========================================

def buscar_en_bd(termino):
    conn = conectar_bd()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM libros WHERE titulo LIKE %s OR autor LIKE %s"
        patron = f"%{termino}%"
        cursor.execute(sql, (patron, patron))
        resultados = cursor.fetchall()

        libros_locales = []
        for row in resultados:
            libros_locales.append({
                'id_libros': row.get('id_libros'),
                'google_id': row.get('google_id'),
                'titulo': row.get('titulo'),
                'autor': row.get('autor'),
                'fecha': row.get('fecha'),
                'sinopsis': row.get('sinopsis') or row.get('sinopsis'),
                'portada': row.get('portada_url') or row.get('portada'),
                'origen': '🏠 LOCAL (MySQL)'
            })
        return libros_locales
    except Exception as e:
        return []
    finally:
        if conn: conn.close()

def buscar_en_google(termino_busqueda):
    query_encoded = urllib.parse.quote(termino_busqueda)
    url = f"https://www.googleapis.com/books/v1/volumes?q={query_encoded}&maxResults=15&printType=books"
    headers = {'User-Agent': 'BookRadarApp/2.0'}
    try:
        respuesta = requests.get(url, headers=headers, timeout=8)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            libros_limpios = []
            if 'items' in datos:
                for item in datos['items']:
                    vol = item.get('volumeInfo', {})
                    libros_limpios.append({
                        'google_id': item.get('id'),
                        'titulo': vol.get('title', 'Sin título'),
                        'autor': vol.get('authors', ['Desconocido'])[0],
                        'fecha': vol.get('publishedDate', 'S/F'),
                        'sinopsis': vol.get('sinopsis', 'Sin sinopsis'),
                        'portada': vol.get('imageLinks', {}).get('thumbnail'),
                        'origen': ' INTERNET (Google)'
                    })
            return libros_limpios
        elif respuesta.status_code == 429:
            return "Límite de API alcanzado. Espera un momento."
        return []
    except Exception:
        return []


@app.route('/perfil')
def vista_perfil():
    """Carga el perfil con el análisis visual de géneros leídos"""
    if 'id_usuario' not in session:
        return redirect(url_for('vista_login'))

    user_id = session['id_usuario']
    conn = conectar_bd()

    usuario = {'nombre_usuario': 'Usuario', 'email': ''}
    generos = []
    favoritos = []
    stats = {
        'total_leidos': 0,
        'top_genero': 'Explorador/a',
        'labels_grafico': [],
        'data_grafico': []
    }

    if not conn:
        return render_template('perfil.html', usuario=usuario, generos=generos, favoritos=favoritos, stats=stats)

    try:
        cursor = conn.cursor(dictionary=True)

        # Obtener datos del usuario
        cursor.execute("SELECT nombre_usuario, email FROM Usuarios WHERE id_usuarios = %s", (user_id,))
        res_user = cursor.fetchone()
        if res_user: usuario = res_user

        # Obtener géneros para la sección de intereses
        cursor.execute("SELECT * FROM generos")
        generos = cursor.fetchall()

        cursor.execute("SELECT id_genero FROM preferencias_usuario WHERE id_usuario = %s", (user_id,))
        favoritos = [f['id_genero'] for f in cursor.fetchall()]

        # ANALIZAR GÉNEROS PARA EL GRÁFICO
        # Solo contamos los libros que el usuario ha marcado como 'LEIDO'
        sql_stats = """
            SELECT l.categorias 
            FROM usuarios_libros ul
            JOIN libros l ON ul.id_libro = l.id_libros
            WHERE ul.id_usuario = %s AND ul.estado = 'LEIDO' AND l.categorias IS NOT NULL
        """
        cursor.execute(sql_stats, (user_id,))
        libros_leidos = cursor.fetchall()

        if libros_leidos:
            conteo = Counter()
            for registro in libros_leidos:
                categorias = [c.strip() for c in registro['categorias'].split(',')]
                for cat in categorias:
                    if cat and cat.lower() != 'general':
                        conteo[cat] += 1

            # Tomamos los 5 géneros más comunes para el gráfico
            top_5 = conteo.most_common(5)
            stats['total_leidos'] = len(libros_leidos)
            stats['labels_grafico'] = [t[0] for t in top_5]
            stats['data_grafico'] = [t[1] for t in top_5]

            if top_5:
                stats['top_genero'] = top_5[0][0]

    except Exception as e:
        print(f"Error cargando estadísticas: {e}")
    finally:
        if conn: conn.close()

    return render_template('perfil.html', usuario=usuario, generos=generos, favoritos=favoritos, stats=stats)


# Vista de recomendaciones híbridas

@app.route('/recomendaciones')
def vista_recomendaciones():
    """
    Genera recomendaciones híbridas basadas en:
    1. Géneros marcados en el perfil.
    2. Categorías de libros leídos.
    3. Categorías de libros puntuados con 4 o 5 estrellas.
    """
    if 'id_usuario' not in session:
        return redirect(url_for('vista_login'))

    user_id = session['id_usuario']
    intereses = set()

    conn = conectar_bd()
    if not conn: return "Error de conexión", 500

    try:
        cursor = conn.cursor(dictionary=True)

        # 1. Géneros explícitos (preferencias del perfil)
        cursor.execute("""
            SELECT g.nombre_genero 
            FROM preferencias_usuario pu
            JOIN generos g ON pu.id_genero = g.id_genero 
            WHERE pu.id_usuario = %s
        """, (user_id,))
        for row in cursor.fetchall():
            intereses.add(row['nombre_genero'])

        # 2. Categorías de libros leídos o bien puntuados con 4 o 5 estrellas
        cursor.execute("""
            SELECT l.categorias 
            FROM usuarios_libros ul
            JOIN libros l ON ul.id_libro = l.id_libros
            WHERE ul.id_usuario = %s 
            AND (ul.estado = 'LEIDO' OR ul.calificacion >= 4)
            AND l.categorias IS NOT NULL
        """, (user_id,))

        for row in cursor.fetchall():
            # Cada libro puede tener varias categorías separadas por comas, las procesamos individualmente
            categorias_lista = [c.strip() for c in row['categorias'].split(',')]
            for cat in categorias_lista:
                if cat and cat != 'General':
                    intereses.add(cat)

        # 3. Obtener los google_id de los libros que el usuario ya tiene en su biblioteca para no recomendarlos
        cursor.execute("""
            SELECT l.google_id 
            FROM usuarios_libros ul
            JOIN libros l ON ul.id_libro = l.id_libros 
            WHERE ul.id_usuario = %s
        """, (user_id,))
        libros_ignorados = [r['google_id'] for r in cursor.fetchall()]

    except mysql.connector.Error as err:
        logging.error(f"Error recuperando intereses: {err}")
    finally:
        conn.close()

    # Si el usuario no tiene intereses claros, usamos algunos por defecto para no mostrar una página vacía
    if not intereses:
        intereses = {"Ficción", "Aventura", "Best-sellers"}

    # Selección aleatoria de intereses para dinamismo (máximo 3)
    terminos_clave = random.sample(list(intereses), min(len(intereses), 3))
    query_api = " + ".join(terminos_clave)
    recomendaciones = []

    try:
        # Llamada a la API de Google Books con los términos clave generados
        url = f"https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(query_api)}&maxResults=20&langRestrict=es"
        resp = requests.get(url, timeout=5)

        if resp.status_code == 200:
            for item in resp.json().get('items', []):
                v = item.get('volumeInfo', {})
                gid = item.get('id')

                # Filtramos para no recomendar libros que el usuario ya tiene en su biblioteca
                if gid not in libros_ignorados:
                    recomendaciones.append({
                        'google_id': gid,
                        'titulo': v.get('title'),
                        'autor': ", ".join(v.get('authors', ['Desconocido'])),
                        'portada': v.get('imageLinks', {}).get('thumbnail'),
                        'genero_origen': terminos_clave[0] # Contexto de la recomendación
                    })
    except Exception as e:
        logging.error(f"Error llamando a Google API: {e}")

    return render_template('recomendaciones.html', recomendaciones=recomendaciones[:12])

@app.route('/libro/<google_id>')
def vista_detalle_libro(google_id):

    url = f"https://www.googleapis.com/books/v1/volumes/{google_id}"
    libro_detalle = None

    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            item = resp.json()
            vol = item.get('volumeInfo', {})
            libro_detalle = {
                'google_id': item.get('id'),
                'titulo': vol.get('title', 'Sin título'),
                'autor': ", ".join(vol.get('authors', ['Desconocido'])),
                'fecha': vol.get('fecha', 'S/F'),
                'descripcion': vol.get('description', 'Sin descripción'),
                'paginas': vol.get('pageCount', '---'),
                'categorias': ", ".join(vol.get('categories', ['General'])),
                'portada': vol.get('imageLinks', {}).get('large') or vol.get('imageLinks', {}).get('thumbnail'),
                'editorial': vol.get('publisher', 'Desconocida'),
                'isbn': vol.get('industryIdentifiers', [{}])[0].get('identifier', '---')
            }
    except Exception as e:
        logging.error(f"Error: {e}")

    if not libro_detalle: return render_template('404.html'), 404

    # Si el usuario está logueado, buscamos si ya tiene este libro en su biblioteca para mostrar estado, calificación y comentario
    estado_actual = None
    calificacion_actual = 0
    comentario_actual = ""

    if 'id_usuario' in session:
        conn = conectar_bd()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                # Buscamos el estado, calificación y comentario del libro para este usuario
                sql = """
                    SELECT ul.estado, ul.calificacion, ul.comentario 
                    FROM usuarios_libros ul 
                    JOIN libros l ON ul.id_libro = l.id_libros 
                    WHERE ul.id_usuario = %s AND l.google_id = %s
                """
                cursor.execute(sql, (session['id_usuario'], google_id))
                res = cursor.fetchone()
                if res:
                    estado_actual = res['estado']
                    calificacion_actual = res['calificacion'] or 0
                    comentario_actual = res['comentario'] or ""
            finally:
                conn.close()

    return render_template('detalles.html',
                           libro=libro_detalle,
                           estado=estado_actual,
                           calificacion=calificacion_actual,
                           comentario=comentario_actual)

# Endpoint para guardar la reseña (comentario) del usuario sobre un libro específico
@app.route('/api/guardar-resena', methods=['POST'])
def api_guardar_resena():
    if 'id_usuario' not in session: return jsonify({'status': 'error'}), 401

    datos = request.json
    google_id = datos.get('google_id')
    # Permitimos que el frontend envíe el comentario con cualquiera de las dos claves para flexibilidad
    comentario = datos.get('resena') or datos.get('comentario')

    conn = conectar_bd()
    try:
        cursor = conn.cursor()
        # Primero, buscamos el ID del libro en nuestra base de datos usando el google_id
        cursor.execute("SELECT id_libros FROM libros WHERE google_id = %s", (google_id,))
        libro = cursor.fetchone()

        if not libro:
            return jsonify({'status': 'error', 'mensaje': 'Libro no encontrado en BD'}), 404

        # Luego, actualizamos el comentario para ese libro y usuario específico
        sql = "UPDATE usuarios_libros SET comentario = %s WHERE id_usuario = %s AND id_libro = %s"
        cursor.execute(sql, (comentario, session['id_usuario'], libro[0]))
        conn.commit()
        return jsonify({'status': 'success', 'mensaje': 'Opinión guardada'})
    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500
    finally:
        conn.close()


# ==========================================
# 3. ENDPOINTS API (JSON)
# ==========================================

@app.route('/api/guardar-libro', methods=['POST'])
def api_guardar():
    if 'id_usuario' not in session:
        return jsonify({'status': 'error', 'mensaje': 'Inicia sesión primero'}), 401

    datos = request.json
    estado = datos.get('estado')

    res = guardar_libro_en_bd(datos, session['id_usuario'], estado)
    return jsonify(res)

@app.route('/api/eliminar-libro/<int:id_libro>', methods=['DELETE'])
def api_eliminar(id_libro):
    if 'id_usuario' not in session: return jsonify({'error': 'No login'}), 401
    conn = conectar_bd()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios_libros WHERE id_usuario = %s AND id_libro = %s",
                       (session['id_usuario'], id_libro))
        conn.commit()
        return jsonify({'status': 'success'})
    finally:
        if conn: conn.close()

@app.route('/api/registro', methods=['POST'])
def api_registro():
    datos = request.json
    hash_pass = generate_password_hash(datos.get('password'))
    conn = conectar_bd()
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO usuarios (nombre_usuario, email, contraseña) VALUES (%s, %s, %s)"
        cursor.execute(sql, (datos.get('usuario'), datos.get('email'), hash_pass))
        conn.commit()
        return jsonify({'status': 'success'})
    except mysql.connector.Error as err:
        return jsonify({'status': 'error', 'mensaje': 'Email ya existe'}), 409
    finally:
        if conn: conn.close()

@app.route('/api/login', methods=['POST'])
def api_login():
    datos = request.json or {}
    email = datos.get('email')
    password = datos.get('password')
    conn = conectar_bd()
    if not conn: return jsonify({'status': 'error', 'mensaje': 'Sin DB'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT id_usuarios, nombre_usuario, contraseña FROM usuarios WHERE email = %s"
        cursor.execute(sql, (email,))
        usuario_db = cursor.fetchone()
        if usuario_db and check_password_hash(usuario_db['contraseña'], password):
            session['id_usuario'] = usuario_db['id_usuarios']
            session['nombre_usuario'] = usuario_db['nombre_usuario']
            return jsonify({'status': 'success', 'id_usuario': usuario_db['id_usuarios']})
        return jsonify({'status': 'error', 'mensaje': 'Acceso denegado'}), 401
    finally:
        if conn: conn.close()

@app.route('/api/test-db')
def test_db():
    conn = conectar_bd()
    if conn:
        conn.close()
        return jsonify({"servidor": "activo", "mysql": "conectado"})
    return jsonify({"servidor": "activo", "mysql": "error"}), 500

@app.route('/api/perfil/actualizar', methods=['POST'])
def api_perfil_actualizar():
    if 'id_usuario' not in session: return jsonify({'status': 'error'}), 401

    datos = request.json
    nuevo_nombre = datos.get('usuario')
    nuevo_email = datos.get('email')
    nueva_pass = datos.get('password')  # <--- Asegúrate que el JS envíe 'password'

    conn = conectar_bd()
    try:
        cursor = conn.cursor()

        if nueva_pass and nueva_pass.strip() != "":
            # CASO A: Hay contraseña nueva
            print("DEBUG: Actualizando con nueva contraseña")
            hash_pass = generate_password_hash(nueva_pass)
            sql = "UPDATE usuarios SET nombre_usuario=%s, email=%s, contraseña=%s WHERE id_usuarios=%s"
            cursor.execute(sql, (nuevo_nombre, nuevo_email, hash_pass, session['id_usuario']))
        else:
            # CASO B: No hay contraseña (solo datos básicos)
            print("DEBUG: Actualizando solo nombre y email")
            sql = "UPDATE usuarios SET nombre_usuario=%s, email=%s WHERE id_usuarios=%s"
            cursor.execute(sql, (nuevo_nombre, nuevo_email, session['id_usuario']))

        conn.commit()
        session['nombre_usuario'] = nuevo_nombre
        return jsonify({'status': 'success', 'mensaje': 'Datos actualizados correctamente'})
    except Exception as e:
        print(f"Error en update: {e}")
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/preferencias', methods=['POST'])
def api_perfil_preferencias():

    if 'id_usuario' not in session: return jsonify({'status': 'error'}), 401

    generos_seleccionados = request.json.get('generos', [])
    user_id = session['id_usuario']

    conn = conectar_bd()
    try:
        cursor = conn.cursor()
        # 1. Eliminamos las preferencias anteriores del usuario para evitar duplicados o conflictos
        cursor.execute("DELETE FROM preferencias_usuario WHERE id_usuario = %s", (user_id,))
        # 2. Insertamos las nuevas preferencias seleccionadas por el usuario
        if generos_seleccionados:
            sql = "INSERT INTO preferencias_usuario (id_usuario, id_genero) VALUES (%s, %s)"
            datos_ins = [(user_id, g_id) for g_id in generos_seleccionados]
            cursor.executemany(sql, datos_ins)

        conn.commit()
        return jsonify({'status': 'success', 'mensaje': 'Preferencias guardadas'})
    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500
    finally: conn.close()

@app.route('/perfil/eliminar', methods=['POST'])
def eliminar_cuenta():
    if 'id_usuario' not in session: return redirect(url_for('vista_inicio'))
    uid = session['id_usuario']
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    cursor.execute("DELETE FROM usuarios WHERE id_usuarios = %s", (uid,))
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()
    conn.close()
    session.clear()
    return redirect(url_for('vista_inicio'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)