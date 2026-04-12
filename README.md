<img src="static/img/logo.png" height="40" align="absmiddle"> BookRadar

Proyecto de Fin de Grado Ciclo Formativo: Desarrollo de Aplicaciones Multiplataforma (CESUR) año 2026. Autor: Ángel Durán Gómez

- Sobre el proyecto

En la actualidad, la inmensa cantidad de contenido literario disponible dificulta a los lectores encontrar su próxima lectura. BookRadar es una aplicación web destinada a centralizar y personalizar el proceso de descubrimiento de libros.

El objetivo principal es resolver el problema de la sobrecarga de información, ofreciendo a los usuarios sugerencias de lectura altamente relevantes basadas en su perfil y su historial de consumo.

- Características Principales (En desarrollo)

Búsqueda Híbrida Inteligente: Motor de búsqueda que prioriza una base de datos local (MySQL) para reducir latencia, respaldado por la Google Books API para consultas externas.

Gestor de Biblioteca Personal: Clasificación de libros en estados: 'Quiero leer', 'Leído' o 'Descartado'.

Motor de Recomendaciones: Sugerencias personalizadas basadas en géneros favoritos y calificaciones previas.

Diseño "Clean UI": Interfaz minimalista orientada a evitar la fatiga visual.

- Stack Tecnológico

El proyecto sigue una arquitectura MVC adaptada a la web:

Backend (Lógica & API)

Python 3.12

Framework: Flask

Conectividad: mysql-connector-python & requests

Frontend (Interfaz de Usuario)

HTML5 (Plantillas Jinja2)

CSS3 (Diseño responsivo y variables nativas)

JavaScript (Vanilla)

Persistencia de Datos

Base de Datos: MySQL 8.0

Integración Externa: Google Books API

- Instalación y Configuración
[cite_start]Siga estos pasos para ejecutar una instancia local del proyecto :

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

4.  **Configuración de la Base de Datos:**
    * [cite_start]Importe el archivo `database_bookradar.sql` en su servidor MySQL local[cite: 587].
    * [cite_start]Ajuste las credenciales de conexión en el archivo `db.py`[cite: 503].

5.  **Ejecución de la aplicación:**
    ```bash
    python app.py
    ```
    [cite_start]Acceda a `http://127.0.0.1:5000` en su navegador[cite: 590].

---
- Estado del Proyecto
  * [cite_start]**Entrega 1:** Análisis y requisitos (Finalizado)
  * [cite_start]**Entrega 2:** Diseño técnico y arquitectura (Finalizado)
  * [cite_start]**Entrega 3:** Implementación estable de registro, búsqueda híbrida, gestión de biblioteca y perfil de usuario (Finalizado)

---

## 📄 Licencia
Este proyecto se distribuye bajo la **Licencia MIT**.