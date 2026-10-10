import pytest

from cache_policy import cache_ttl


@pytest.mark.parametrize(
    ("nombre", "descripcion", "esperado"),
    [
        ("Auto", "Uso urbano", 15),
        ("Vehiculo", "Uso urbano", 20),
        ("VehiculoDemo", "Uso urbano", 40),
        ("Auto", "Descripción de veintiún x", None),
    ],
)
def test_tiempos_de_cache(nombre, descripcion, esperado):
    assert cache_ttl(nombre, descripcion) == esperado


def test_descripcion_larga_tiene_prioridad():
    assert cache_ttl("VehiculoDemo", "Una descripción con más de veinte caracteres") is None
