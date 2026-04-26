<div align="center">
  <img src="static/img/logo.png" height="80" alt="BookRadar Logo">
  <h1>BookRadar</h1>
  <p><b>Proyecto de Fin de Grado</b> | Desarrollo de Aplicaciones Multiplataforma (CESUR) 2026</p>
  <p>Autor: Ángel Durán Gómez</p>
</div>

---

##  Sobre el proyecto
En la actualidad, la inmensa cantidad de contenido literario disponible dificulta a los lectores encontrar su próxima lectura. **BookRadar** es una aplicación web destinada a centralizar y personalizar el proceso de descubrimiento de libros.

El objetivo principal es resolver el problema de la sobrecarga de información, ofreciendo a los usuarios sugerencias de lectura altamente relevantes basadas en su perfil, su historial de consumo y el análisis inteligente de sus reseñas.

##  Características Principales

* **Búsqueda Híbrida Inteligente:** Motor de búsqueda que prioriza una base de datos local (MySQL) para reducir latencia, respaldado por la Google Books API para consultas externas.
* **Gestor de Biblioteca Personal:** Clasificación de libros en estados ('Quiero leer', 'Leído' o 'Descartado') y sistema de calificaciones.
* **Inteligencia Artificial (NLP):** Análisis de sentimiento en las reseñas usando TextBlob para detectar el "ADN lector" (polaridad positiva/negativa) y afinar el motor de sugerencias.
* **Motor de Recomendaciones Concurrente:** Sugerencias personalizadas renderizadas en tiempo real gracias a la optimización de hilos paralelos (`ThreadPoolExecutor`).
* **Diseño Responsive y "Clean UI":** Interfaz moderna adaptada a dispositivos móviles y navegación asíncrona sin recargas (Fetch API) orientada a evitar la fatiga visual.

## 🛠️ Stack Tecnológico

**Backend (Lógica & Servidor)**
* **Lenguaje:** Python 3.12
* **Framework:** Flask (Renderizado dinámico con Jinja2)
* **IA & Concurrencia:** TextBlob (NLP) y `concurrent.futures`
* **Testing:** Pytest

**Frontend (Interfaz de Usuario)**
* HTML5 & CSS3 (Media queries para diseño móvil)
* JavaScript (Vanilla) con Fetch API
* Librería Gráfica: Chart.js

**Persistencia de Datos y Seguridad**
* **Base de Datos:** MySQL 8.0 (mysql-connector-python)
* **Integración Externa:** Google Books API (Librería `requests`)
* **Seguridad:** Werkzeug (Hashing de contraseñas) y validación de sesiones.

## ⚙️ Instalación y Configuración

Siga estos pasos para ejecutar una instancia local del proyecto:

1.  **Clonación del repositorio:**
    ```bash
    git clone [https://github.com/ANGELDG-94/BookRadar.git](https://github.com/ANGELDG-94/BookRadar.git)
    cd BookRadar
    ```

2.  **Creación del entorno virtual:**
    ```bash
    python -m venv .venv
    # Activar en Windows:
    .venv\Scripts\activate
    ```

3.  **Instalación de dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Descarga de diccionarios NLP (Obligatorio para IA):**
    ```bash
    python -m textblob.download_corpora
    ```

5.  **Configuración de la Base de Datos:**
    * Importe el archivo `database_bookradar.sql` en su servidor MySQL local.
    * Ajuste las credenciales de conexión en el archivo `db.py`.

6.  **Ejecución de la aplicación:**
    ```bash
    python app.py
    ```
    Acceda a `http://127.0.0.1:5000` en su navegador.

---
##  Estado del Proyecto
* **Proyecto Finalizado (Entrega Final):** Análisis, diseño técnico, arquitectura híbrida, interfaz responsiva, pruebas automatizadas e integración de Inteligencia Artificial completados con éxito.

---
## 📄 Licencia
Este proyecto se distribuye bajo la **Licencia MIT**.