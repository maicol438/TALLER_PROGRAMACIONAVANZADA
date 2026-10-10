"""API REST de vehículos con MongoDB y caché Redis."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from redis import Redis
from redis.exceptions import RedisError

from cache_policy import cache_ttl
from seed_data import VEHICULOS


REQUIRED_FIELDS = {"nombre", "categoria", "peso_toneladas", "descripcion"}


def create_app(test_config: dict[str, Any] | None = None, mongo_client=None, redis_client=None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        MONGO_URI=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        MONGO_DB=os.getenv("MONGO_DB", "automoviles"),
        REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    )
    if test_config:
        app.config.update(test_config)

    mongo_client = mongo_client or MongoClient(app.config["MONGO_URI"])
    redis_client = redis_client or Redis.from_url(app.config["REDIS_URL"], decode_responses=True)
    collection = mongo_client[app.config["MONGO_DB"]]["vehiculos"]
    indexes_ready = False

    def ensure_indexes() -> None:
        """Crea el índice al primer acceso para no fallar si Mongo aún inicia."""
        nonlocal indexes_ready
        if not indexes_ready:
            collection.create_index("nombre_normalizado", unique=True)
            indexes_ready = True

    def cache_key(vehicle_id: str) -> str:
        return f"vehiculo:{vehicle_id}"

    def serialize(document: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(document["_id"]),
            "nombre": document["nombre"],
            "categoria": document["categoria"],
            "peso_toneladas": document["peso_toneladas"],
            "descripcion": document["descripcion"],
        }

    def normalize_name(value: str) -> str:
        return value.strip().casefold()

    def validate_vehicle(payload: Any, partial: bool = False) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(payload, dict):
            return None, "El cuerpo debe ser un objeto JSON."
        allowed = REQUIRED_FIELDS
        unknown = set(payload) - allowed
        if unknown:
            return None, f"Campos no permitidos: {', '.join(sorted(unknown))}."
        if not partial and set(payload) != REQUIRED_FIELDS:
            missing = REQUIRED_FIELDS - set(payload)
            return None, f"Faltan campos requeridos: {', '.join(sorted(missing))}."
        if partial and not payload:
            return None, "Debe enviar al menos un campo para actualizar."

        data = dict(payload)
        for field in ("nombre", "categoria", "descripcion"):
            if field in data:
                if not isinstance(data[field], str) or not data[field].strip():
                    return None, f"{field} debe ser texto no vacío."
                data[field] = data[field].strip()
        if "peso_toneladas" in data:
            if isinstance(data["peso_toneladas"], bool) or not isinstance(data["peso_toneladas"], (int, float)):
                return None, "peso_toneladas debe ser numérico."
            if data["peso_toneladas"] <= 0:
                return None, "peso_toneladas debe ser mayor que cero."
        if "nombre" in data:
            data["nombre_normalizado"] = normalize_name(data["nombre"])
        return data, None

    def object_id(value: str) -> ObjectId | None:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None

    def invalidate(vehicle_id: str) -> None:
        try:
            redis_client.delete(cache_key(vehicle_id))
        except RedisError:
            app.logger.warning("Redis no disponible; no se pudo invalidar la caché.")

    @app.get("/salud")
    def health():
        return {"estado": "ok"}

    @app.post("/vehiculos")
    def create_vehicle():
        ensure_indexes()
        data, error = validate_vehicle(request.get_json(silent=True))
        if error:
            return {"error": error}, 400
        data["creado_en"] = datetime.now(timezone.utc)
        try:
            result = collection.insert_one(data)
        except DuplicateKeyError:
            return {"error": "Ya existe un vehículo con ese nombre."}, 409
        vehicle = collection.find_one({"_id": result.inserted_id})
        return jsonify(serialize(vehicle)), 201

    @app.get("/vehiculos")
    def list_vehicles():
        ensure_indexes()
        vehicles = [serialize(doc) for doc in collection.find().sort("nombre", 1)]
        return jsonify({"total": len(vehicles), "vehiculos": vehicles, "fuente": "mongodb"})

    @app.get("/vehiculos/<vehicle_id>")
    def get_vehicle(vehicle_id: str):
        ensure_indexes()
        oid = object_id(vehicle_id)
        if not oid:
            return {"error": "Identificador de vehículo inválido."}, 400

        try:
            cached = redis_client.get(cache_key(vehicle_id))
            if cached:
                vehicle = json.loads(cached)
                vehicle["fuente"] = "redis"
                return jsonify(vehicle)
        except (RedisError, json.JSONDecodeError):
            app.logger.warning("No fue posible leer Redis; se consulta MongoDB.")

        document = collection.find_one({"_id": oid})
        if not document:
            return {"error": "Vehículo no encontrado."}, 404
        vehicle = serialize(document)
        ttl = cache_ttl(vehicle["nombre"], vehicle["descripcion"])
        if ttl is not None:
            try:
                redis_client.setex(cache_key(vehicle_id), ttl, json.dumps(vehicle, ensure_ascii=False))
            except RedisError:
                app.logger.warning("No fue posible guardar en Redis; se responde desde MongoDB.")
        vehicle["fuente"] = "mongodb"
        vehicle["cache_ttl_segundos"] = ttl
        return jsonify(vehicle)

    @app.put("/vehiculos/<vehicle_id>")
    def update_vehicle(vehicle_id: str):
        ensure_indexes()
        oid = object_id(vehicle_id)
        if not oid:
            return {"error": "Identificador de vehículo inválido."}, 400
        data, error = validate_vehicle(request.get_json(silent=True), partial=True)
        if error:
            return {"error": error}, 400
        try:
            updated = collection.find_one_and_update(
                {"_id": oid}, {"$set": data}, return_document=True
            )
        except DuplicateKeyError:
            return {"error": "Ya existe un vehículo con ese nombre."}, 409
        if not updated:
            return {"error": "Vehículo no encontrado."}, 404
        invalidate(vehicle_id)
        return jsonify(serialize(updated))

    @app.delete("/vehiculos/<vehicle_id>")
    def delete_vehicle(vehicle_id: str):
        ensure_indexes()
        oid = object_id(vehicle_id)
        if not oid:
            return {"error": "Identificador de vehículo inválido."}, 400
        result = collection.delete_one({"_id": oid})
        if not result.deleted_count:
            return {"error": "Vehículo no encontrado."}, 404
        invalidate(vehicle_id)
        return "", 204

    @app.cli.command("seed")
    def seed() -> None:
        """Carga o actualiza los diez registros de la imagen de referencia."""
        ensure_indexes()
        for vehicle in VEHICULOS:
            document = dict(vehicle)
            document["nombre_normalizado"] = normalize_name(document["nombre"])
            collection.update_one(
                {"nombre_normalizado": document["nombre_normalizado"]},
                {"$set": document, "$setOnInsert": {"creado_en": datetime.now(timezone.utc)}},
                upsert=True,
            )
        print(f"Se cargaron/actualizaron {len(VEHICULOS)} vehículos.")

    return app


app = create_app()
