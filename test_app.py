import data
import pytest
from app import app

@pytest.fixture
def client():

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
    assert response.status_code == 200


# TEST 3: Seguridad - Protección de rutas
def test_profile_no_login(client):
    response = client.get('/mis-libros')
    assert response.status_code == 302 or response.status_code == 401
