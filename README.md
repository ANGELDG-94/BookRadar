<img src="static/img/logo.png" height="40" align="absmiddle"> BookRadar

Proyecto de Fin de Grado Ciclo Formativo: Desarrollo de Aplicaciones Multiplataforma (CESUR) año 2026. Autor: Ángel Durán Gómez

📖 Sobre el proyecto

En la actualidad, la inmensa cantidad de contenido literario disponible dificulta a los lectores encontrar su próxima lectura. BookRadar es una aplicación web destinada a centralizar y personalizar el proceso de descubrimiento de libros.

El objetivo principal es resolver el problema de la sobrecarga de información, ofreciendo a los usuarios sugerencias de lectura altamente relevantes basadas en su perfil y su historial de consumo.

📋 Características Principales (En desarrollo)

Búsqueda Híbrida Inteligente: Motor de búsqueda que prioriza una base de datos local (MySQL) para reducir latencia, respaldado por la Google Books API para consultas externas.

Gestor de Biblioteca Personal: Clasificación de libros en estados: 'Quiero leer', 'Leído' o 'Descartado'.

Motor de Recomendaciones: Sugerencias personalizadas basadas en géneros favoritos y calificaciones previas.

Diseño "Clean UI": Interfaz minimalista orientada a evitar la fatiga visual.

🛠️ Stack Tecnológico

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

📋 Estado del Proyecto

Actualmente, el proyecto ha completado la Entrega 2 (Diseño Técnico e Implementación Base).

En cuanto a Backend, se esta trabajando en el registro de usuarios, la gestión de la biblioteca personal y el motor de recomendaciones.

En el Frontend, se ha realizado un primer boceto de la interfaz de usuario, con un enfoque en la simplicidad y la usabilidad. Al que se le han adherido una paleta de colores neutra y tipografía legible para mejorar la experiencia del usuario.
Y se esta trabajando en las distintas ventanas de la aplicación, como el panel de control del usuario, la página de búsqueda y la sección de recomendaciones.

📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo LICENSE en este repositorio para más detalles.