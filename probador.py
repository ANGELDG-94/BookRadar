import requests
import json
import time

# URL de tu servidor local
BASE_URL = "http://127.0.0.1:5000/api"

def probar_flujo():
    print("\n--- 1. BUSCANDO LIBRO 'pilares de la tierra' (Primera vez) ---")

    try:
        # 1. Buscamos en tu API (que buscará en MySQL o Google)
        resp = requests.get(f"{BASE_URL}/buscar?q=pilares de la tierra")

        if resp.status_code == 200:
            libros = resp.json()
            if libros:
                # Cogemos el primer resultado
                primer_libro = libros[0]
                print(f"Encontrado: {primer_libro['titulo']}")
                print(f"Origen: {primer_libro.get('origen', 'Desconocido')}")

                print("\n--- 2. GUARDANDO EN MYSQL ---")

                # 2. Enviamos ese libro para guardar (POST)
                resp_guardar = requests.post(f"{BASE_URL}/guardar-libro", json=primer_libro)

                print("Respuesta del servidor al guardar:")
                # Imprimimos la respuesta exacta para ver si hay error SQL
                print(json.dumps(resp_guardar.json(), indent=2))

                print("\n--- 3. VERIFICANDO PERSISTENCIA (Buscando de nuevo) ---")
                time.sleep(1) # Esperamos un poco

                resp_verificacion = requests.get(f"{BASE_URL}/buscar?q=Dune")
                libros_v = resp_verificacion.json()

                if libros_v:
                    print(f"Origen segunda búsqueda: {libros_v[0].get('origen', 'Desconocido')}")
                    if "LOCAL" in libros_v[0].get('origen', ''):
                        print("¡ÉXITO! El sistema funciona.")
                    else:
                        print("FALLO: Sigue buscando en Google. Revisa la base de datos.")

            else:
                print("No se encontraron libros.")
        else:
            print(f"Error en búsqueda: {resp.status_code}")

    except Exception as e:
        print(f"Error conectando al servidor: {e}")
        print("¿Está app.py ejecutándose?")

if __name__ == "__main__":
    probar_flujo()