import data
import pytest
from app import app

@pytest.fixture
def client():
    # Configuramos la app para modo test
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# TEST 1: Verificar que la Home carga correctamente (Status 200)
def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"BookRadar" in response.data # Verifica que el nombre del proyecto está en el HTML

# TEST 2: Verificar el buscador (API interna)
def test_api_search(client):
    response = client.get('/buscar?q=principito')
    # Lo más importante: ¿La ruta existe y responde?
    assert response.status_code == 200
    # Si devuelve algo, perfecto, si no, al menos sabemos que no ha dado error 500

# TEST 3: Seguridad - Protección de rutas
def test_profile_no_login(client):
    # Si intentamos entrar al perfil sin estar logueados, debe redirigir (302)
    response = client.get('/mis-libros')
    assert response.status_code == 302 or response.status_code == 401
