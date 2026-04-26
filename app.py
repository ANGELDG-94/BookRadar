import logging
import os
import random
import urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from textblob import TextBlob
import mysql.connector
import requests
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from db import conectar_bd

# ==========================================
# CONFIGURACIÓN
# ==========================================
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'super_secreta_bookradar_2026_clave_unica')

cache_busquedas = {}

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
            libros = []
            for item in items:
                vol = item.get('volumeInfo', {})
                image_links = vol.get('imageLinks', None)
                if image_links and 'thumbnail' in image_links:
                    portada = image_links['thumbnail'].replace('http://', 'https://').replace('&zoom=5', '&zoom=1')
                else:
                    titulo_esc = urllib.parse.quote(vol.get('title', 'Libro'))
                    portada = f"https://ui-avatars.com/api/?name={titulo_esc}&size=300&background=f1f5f9&color=64748b&format=svg"

                libros.append({
                    'google_id': item.get('id'),
                    'titulo': vol.get('title', 'Sin título'),
                    'autor': ", ".join(vol.get('authors', ['Desconocido'])),
                    'portada': portada,
                    'puntuacion': vol.get('averageRating', 0)
                })
            return libros
    except Exception as e:
        logging.error(f"Error fetch_books_category: {e}")
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
                datos_libro.get('fecha', 'S/F'),
                datos_libro.get('portada') or datos_libro.get('portada_url', ''),
                datos_libro.get('sinopsis') or datos_libro.get('descripcion') or 'Sin descripción'
            ))
            id_libro_db = cursor.lastrowid

        calif = datos_libro.get('calificacion') or 0
        resena = datos_libro.get('resena') or datos_libro.get('comentario') or ''

        sql_rel = """
                  INSERT INTO usuarios_libros (id_usuario, id_libro, estado, calificacion, comentario)
                  VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY 
                  UPDATE 
                      estado = VALUES(estado), 
                      calificacion = IF(VALUES(calificacion) > 0, VALUES(calificacion), calificacion), 
                      comentario = IF(VALUES(comentario) != '', VALUES(comentario), comentario)
                  """
        cursor.execute(sql_rel, (user_id, id_libro_db, estado, int(calif), resena))
        conn.commit()
        return {'status': 'success', 'id_libro_db': id_libro_db}

    except Exception as e:
        if conn: conn.rollback()
        logging.error(f"Error BD al guardar: {e}")
        return {'status': 'error', 'mensaje': str(e)}
    finally:
        if conn: conn.close()

def analizar_sentimiento(comentario):
    try:
        analisis = TextBlob(comentario)
        polaridad = analisis.sentiment.polarity
        if polaridad > 0.1: return "Positiva"
        elif polaridad < -0.1: return "Negativa"
        else: return "Neutral"
    except:
        return "Neutral"

# ==========================================
# 1. RUTAS DE NAVEGACIÓN (Vistas HTML)
# ==========================================

@app.route('/')
def vista_inicio():
    if 'id_usuario' in session:
        uid = session['id_usuario']
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM preferencias_usuario WHERE id_usuario = %s", (uid,))
            conteo = cursor.fetchone()[0]
            conn.close()
            if conteo < 3:
                return redirect(url_for('vista_registro_paso2'))

    secciones_config = [
        {"id": "tendencias", "titulo": "Novedades y Tendencias", "query": "subject:fiction", "order": "newest"},
        {"id": "misterio", "titulo": "Misterio y Suspense", "query": "subject:mystery", "order": "relevance"},
        {"id": "clasicos", "titulo": "Clásicos Imprescindibles", "query": "subject:classic+literature", "order": "relevance"}
    ]

    if 'id_usuario' in session:
        conn = conectar_bd()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT g.nombre_genero FROM preferencias_usuario pu 
                JOIN generos g ON pu.id_genero = g.id_genero 
                WHERE pu.id_usuario = %s LIMIT 1
            """, (session['id_usuario'],))
            res = cursor.fetchone()
            conn.close()

            if res:
                genero_fav = res['nombre_genero']
                secciones_config.insert(0, {
                    "id": "sugerencias_ia",
                    "titulo": f"Especialmente para ti: {genero_fav}",
                    "query": f"subject:{genero_fav}",
                    "order": "relevance"
                })

    secciones_datos = {}
    with ThreadPoolExecutor() as executor:
        futuros = {executor.submit(fetch_books_category, s["query"], s["order"], 12): s["id"] for s in secciones_config}
        for futuro in as_completed(futuros):
            cat_id = futuros[futuro]
            try:
                secciones_datos[cat_id] = futuro.result()
            except:
                secciones_datos[cat_id] = []

    return render_template('index.html', secciones=secciones_config, datos=secciones_datos)

@app.route('/registro', methods=['GET', 'POST'])
def vista_registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = generate_password_hash(request.form.get('password'))

        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO usuarios (nombre_usuario, email, contraseña) VALUES (%s, %s, %s)",
                           (nombre, email, password))
            uid = cursor.lastrowid
            conn.commit()

            session.clear()
            session['id_usuario'] = uid
            session['nombre_usuario'] = nombre

            return redirect(url_for('vista_registro_paso2'))
        except:
            return render_template('registro.html', error="El email ya está en uso.")
        finally:
            if conn: conn.close()
    return render_template('registro.html')

@app.route('/registro-paso2', methods=['GET', 'POST'])
def vista_registro_paso2():
    if 'id_usuario' not in session:
        return redirect(url_for('vista_login'))

    conn = conectar_bd()
    if not conn: return "Error de conexión", 500

    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        generos_seleccionados = request.form.getlist('generos')
        uid = session['id_usuario']

        if len(generos_seleccionados) < 3:
            cursor.execute("SELECT * FROM generos")
            todos = cursor.fetchall()
            conn.close()
            return render_template('registro_paso2.html', generos=todos, error="Selecciona al menos 3 categorías.")

        try:
            cursor.execute("DELETE FROM preferencias_usuario WHERE id_usuario = %s", (uid,))
            for gid in generos_seleccionados:
                cursor.execute("INSERT INTO preferencias_usuario (id_usuario, id_genero) VALUES (%s, %s)", (uid, gid))
            conn.commit()
            return redirect(url_for('vista_inicio'))
        except Exception as e:
            conn.rollback()
            logging.error(f"Error guardando preferencias: {e}")
            cursor.execute("SELECT * FROM generos")
            todos = cursor.fetchall()
            return render_template('registro_paso2.html', generos=todos, error="Error interno al guardar.")
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
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id_usuarios, nombre_usuario, contraseña FROM usuarios WHERE email = %s", (email,))
            usuario = cursor.fetchone()
            conn.close()

            if usuario and check_password_hash(usuario['contraseña'], password):
                session.clear()
                session['id_usuario'] = usuario['id_usuarios']
                session['nombre_usuario'] = usuario['nombre_usuario']
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

    cache_key = f"{query}_{genero}_{orden}".lower()

    if cache_key in cache_busquedas:
        libros_resultado = cache_busquedas[cache_key]
    else:
        libros_resultado = []
        if query or genero:
            if query and genero: full_query = f"{query} + subject:{genero}"
            elif genero: full_query = f"subject:{genero}"
            else: full_query = query

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
                    if libros_resultado:
                        cache_busquedas[cache_key] = libros_resultado
            except Exception as e:
                logging.error(f"Error en búsqueda API: {e}")

    generos_lista = ["Ficción", "Misterio", "Terror", "Romance", "Ciencia Ficción", "Fantasía", "Historia", "Biografía", "Infantil", "Autoayuda"]
    return render_template('buscar.html', libros=libros_resultado, query=query, genero_sel=genero, orden_sel=orden, generos=generos_lista)

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
                SELECT l.*, ul.estado, ul.sentimiento 
                FROM libros l
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

@app.route('/perfil')
def vista_perfil():
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
        cursor.execute("SELECT nombre_usuario, email FROM usuarios WHERE id_usuarios = %s", (user_id,))
        res_user = cursor.fetchone()
        if res_user: usuario = res_user

        cursor.execute("SELECT * FROM generos")
        generos = cursor.fetchall()

        cursor.execute("SELECT id_genero FROM preferencias_usuario WHERE id_usuario = %s", (user_id,))
        favoritos = [f['id_genero'] for f in cursor.fetchall()]

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

            top_5 = conteo.most_common(5)
            stats['total_leidos'] = len(libros_leidos)
            stats['labels_grafico'] = [t[0] for t in top_5]
            stats['data_grafico'] = [t[1] for t in top_5]
            if top_5: stats['top_genero'] = top_5[0][0]

    except Exception as e:
        logging.error(f"Error cargando estadísticas: {e}")
    finally:
        if conn: conn.close()

    return render_template('perfil.html', usuario=usuario, generos=generos, favoritos=favoritos, stats=stats)

@app.route('/recomendaciones')
def vista_recomendaciones():
    if 'id_usuario' not in session:
        return redirect(url_for('vista_login'))

    user_id = session['id_usuario']
    conn = conectar_bd()
    if not conn: return "Error de conexión", 500

    recomendaciones = []
    terminos_busqueda = []

    try:
        cursor = conn.cursor(dictionary=True)
        sql_ia = """
            SELECT l.autor 
            FROM usuarios_libros ul
            JOIN libros l ON ul.id_libro = l.id_libros
            WHERE ul.id_usuario = %s AND ul.sentimiento = 'Positiva'
            GROUP BY l.autor
            ORDER BY MAX(ul.fecha_guardado) DESC 
            LIMIT 2
            """
        cursor.execute(sql_ia, (user_id,))
        autores_top = [r['autor'] for r in cursor.fetchall()]
        for autor in autores_top:
            terminos_busqueda.append(f"inauthor:{autor}")

        if len(terminos_busqueda) < 2:
            cursor.execute("""
                SELECT g.nombre_genero FROM preferencias_usuario pu
                JOIN generos g ON pu.id_genero = g.id_genero 
                WHERE pu.id_usuario = %s LIMIT 2
            """, (user_id,))
            for row in cursor.fetchall():
                terminos_busqueda.append(f"subject:{row['nombre_genero']}")

        cursor.execute("SELECT l.google_id FROM usuarios_libros ul JOIN libros l ON ul.id_libro = l.id_libros WHERE ul.id_usuario = %s", (user_id,))
        ignorados = [r['google_id'] for r in cursor.fetchall()]

    finally:
        conn.close()

    if not terminos_busqueda:
        terminos_busqueda = ["subject:fiction", "subject:novedades"]

    for query in terminos_busqueda:
        query_encoded = urllib.parse.quote(query)
        url = f"https://www.googleapis.com/books/v1/volumes?q={query_encoded}&maxResults=10&orderBy=relevance&printType=books&langRestrict=es"
        try:
            respuesta = requests.get(url, timeout=8)
            if respuesta.status_code == 200:
                for item in respuesta.json().get('items', []):
                    vol = item.get('volumeInfo', {})
                    if item.get('id') not in ignorados:
                        img_links = vol.get('imageLinks', None)
                        if img_links and 'thumbnail' in img_links:
                            portada_url = img_links['thumbnail'].replace('http://', 'https://').replace('&zoom=5', '&zoom=1')
                        else:
                            portada_url = ""

                        recomendaciones.append({
                            'google_id': item.get('id'),
                            'titulo': vol.get('title', 'Sin título'),
                            'autor': vol.get('authors', ['Desconocido'])[0] if vol.get('authors') else 'Desconocido',
                            'portada': portada_url,
                            'genero_origen': query.replace('subject:', 'Género ').replace('inauthor:', 'Autor ')
                        })
        except Exception as e:
            logging.error(f"Error recomendaciones: {e}")

    random.shuffle(recomendaciones)
    return render_template('recomendaciones.html', recomendaciones=recomendaciones[:15])

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
                'fecha': vol.get('publishedDate', 'S/F'),
                'descripcion': vol.get('description', 'Sin descripción'),
                'paginas': vol.get('pageCount', '---'),
                'categorias': ", ".join(vol.get('categories', ['General'])),
                'portada': vol.get('imageLinks', {}).get('large') or vol.get('imageLinks', {}).get('thumbnail'),
                'editorial': vol.get('publisher', 'Desconocida'),
                'isbn': vol.get('industryIdentifiers', [{}])[0].get('identifier', '---') if vol.get('industryIdentifiers') else '---'
            }
    except Exception as e:
        logging.error(f"Error detalle libro: {e}")

    if not libro_detalle: return render_template('404.html'), 404

    estado_actual = None
    calificacion_actual = 0
    comentario_actual = ""

    if 'id_usuario' in session:
        conn = conectar_bd()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
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

    return render_template('detalles.html', libro=libro_detalle, estado=estado_actual, calificacion=calificacion_actual, comentario=comentario_actual)


# ==========================================
# 3. ENDPOINTS API (JSON)
# ==========================================

@app.route('/api/guardar-resena', methods=['POST'])
def api_guardar_resena():
    if 'id_usuario' not in session: return jsonify({'status': 'error'}), 401

    datos = request.json
    google_id = datos.get('google_id')
    comentario = datos.get('resena') or datos.get('comentario')

    conn = conectar_bd()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_libros FROM libros WHERE google_id = %s", (google_id,))
        libro = cursor.fetchone()

        if not libro:
            return jsonify({'status': 'error', 'mensaje': 'Libro no encontrado en BD'}), 404

        sql = "UPDATE usuarios_libros SET comentario = %s WHERE id_usuario = %s AND id_libro = %s"
        cursor.execute(sql, (comentario, session['id_usuario'], libro[0]))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/guardar-libro', methods=['POST'])
def api_guardar():
    if 'id_usuario' not in session:
        return jsonify({'status': 'error', 'mensaje': 'Inicia sesión primero'}), 401

    datos = request.json
    estado = datos.get('estado')
    id_usuario = session.get('id_usuario')
    comentario = datos.get('comentario') or datos.get('resena') or ''

    res = guardar_libro_en_bd(datos, id_usuario, estado)

    resultado_ia = None
    if res.get('status') == 'success' and comentario:
        resultado_ia = analizar_sentimiento(comentario)
        try:
            db = conectar_bd()
            cursor = db.cursor()
            id_libro_db = res.get('id_libro_db')
            sql = "UPDATE usuarios_libros SET sentimiento = %s WHERE id_usuario = %s AND id_libro = %s"
            cursor.execute(sql, (resultado_ia, id_usuario, id_libro_db))
            db.commit()
            db.close()
        except:
            pass

    res['sentimiento_ia'] = resultado_ia or 'Neutral'
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
        uid = cursor.lastrowid
        conn.commit()

        session.clear()
        session['id_usuario'] = uid
        session['nombre_usuario'] = datos.get('usuario')

        return jsonify({'status': 'success'})
    except mysql.connector.Error:
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
            session.clear()
            session['id_usuario'] = usuario_db['id_usuarios']
            session['nombre_usuario'] = usuario_db['nombre_usuario']
            return jsonify({'status': 'success', 'id_usuario': usuario_db['id_usuarios']})
        return jsonify({'status': 'error', 'mensaje': 'Acceso denegado'}), 401
    finally:
        if conn: conn.close()

@app.route('/api/perfil/actualizar', methods=['POST'])
def api_perfil_actualizar():
    if 'id_usuario' not in session: return jsonify({'status': 'error'}), 401

    datos = request.json
    nuevo_nombre = datos.get('usuario')
    nuevo_email = datos.get('email')
    nueva_pass = datos.get('password')

    conn = conectar_bd()
    try:
        cursor = conn.cursor()

        if nueva_pass and nueva_pass.strip() != "":
            hash_pass = generate_password_hash(nueva_pass)
            sql = "UPDATE usuarios SET nombre_usuario=%s, email=%s, contraseña=%s WHERE id_usuarios=%s"
            cursor.execute(sql, (nuevo_nombre, nuevo_email, hash_pass, session['id_usuario']))
        else:
            sql = "UPDATE usuarios SET nombre_usuario=%s, email=%s WHERE id_usuarios=%s"
            cursor.execute(sql, (nuevo_nombre, nuevo_email, session['id_usuario']))

        conn.commit()
        session['nombre_usuario'] = nuevo_nombre
        return jsonify({'status': 'success'})
    except Exception as e:
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
        cursor.execute("DELETE FROM preferencias_usuario WHERE id_usuario = %s", (user_id,))
        if generos_seleccionados:
            sql = "INSERT INTO preferencias_usuario (id_usuario, id_genero) VALUES (%s, %s)"
            datos_ins = [(user_id, g_id) for g_id in generos_seleccionados]
            cursor.executemany(sql, datos_ins)

        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500
    finally: conn.close()

@app.route('/perfil/eliminar', methods=['POST'])
def eliminar_cuenta():
    if 'id_usuario' not in session: return redirect(url_for('vista_inicio'))
    uid = session['id_usuario']
    conn = conectar_bd()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("DELETE FROM usuarios WHERE id_usuarios = %s", (uid,))
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        conn.close()
    session.clear()
    return redirect(url_for('vista_inicio'))

@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def error_interno_servidor(e):
    return render_template('404.html', mensaje="Error interno del radar"), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)