"""Reglas de expiración requeridas por el taller."""


def cache_ttl(nombre: str, descripcion: str) -> int | None:
    """Devuelve TTL en segundos o None cuando el vehículo no debe cachearse.

    La descripción tiene prioridad, tal como indican las especificaciones.
    El campo identificador elegido es ``nombre``.
    """
    if len(descripcion) > 20:
        return None
    if len(nombre) <= 5:
        return 15
    if len(nombre) <= 10:
        return 20
    return 40
