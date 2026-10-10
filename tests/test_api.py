import fakeredis
import mongomock
import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app(
        {"TESTING": True, "MONGO_DB": "pruebas"},
        mongo_client=mongomock.MongoClient(),
        redis_client=fakeredis.FakeRedis(decode_responses=True),
    )
    return app.test_client()


def vehicle_payload(**changes):
    data = {
        "nombre": "Auto",
        "categoria": "Terrestre (motorizado)",
        "peso_toneladas": 1.5,
        "descripcion": "Uso urbano",
    }
    data.update(changes)
    return data


def test_crud_y_cache_redis(client):
    created = client.post("/vehiculos", json=vehicle_payload())
    assert created.status_code == 201
    vehicle_id = created.get_json()["id"]

    first_get = client.get(f"/vehiculos/{vehicle_id}")
    assert first_get.status_code == 200
    assert first_get.get_json()["fuente"] == "mongodb"
    assert first_get.get_json()["cache_ttl_segundos"] == 15

    second_get = client.get(f"/vehiculos/{vehicle_id}")
    assert second_get.status_code == 200
    assert second_get.get_json()["fuente"] == "redis"

    updated = client.put(f"/vehiculos/{vehicle_id}", json={"descripcion": "Actualizado"})
    assert updated.status_code == 200
    after_update = client.get(f"/vehiculos/{vehicle_id}")
    assert after_update.get_json()["fuente"] == "mongodb"
    assert after_update.get_json()["descripcion"] == "Actualizado"

    deleted = client.delete(f"/vehiculos/{vehicle_id}")
    assert deleted.status_code == 204
    assert client.get(f"/vehiculos/{vehicle_id}").status_code == 404


def test_descripcion_larga_no_se_guarda_en_redis(client):
    created = client.post(
        "/vehiculos",
        json=vehicle_payload(descripcion="Descripción con más de veinte caracteres"),
    )
    vehicle_id = created.get_json()["id"]
    assert client.get(f"/vehiculos/{vehicle_id}").get_json()["fuente"] == "mongodb"
    assert client.get(f"/vehiculos/{vehicle_id}").get_json()["cache_ttl_segundos"] is None
    assert client.get(f"/vehiculos/{vehicle_id}").get_json()["fuente"] == "mongodb"
