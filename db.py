import mysql.connector

# Configuración separada (más limpio)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'JfFN7fbtwPoxddpjHxtb',
    'database': 'bookradar'
}

def conectar_bd():
    """Intenta conectar con la base de datos y devuelve la conexión"""
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        return conexion
    except mysql.connector.Error as err:
        print(f"Error conectando a MySQL: {err}")
        return None