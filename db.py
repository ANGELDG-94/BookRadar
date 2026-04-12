import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'JfFN7fbtwPoxddpjHxtb',
    'database': 'bookradar'
}

def conectar_bd():

    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        return conexion
    except mysql.connector.Error as err:
        print(f"Error conectando a MySQL: {err}")
        return None