# Taller API Vehículos — Flask + MongoDB + Redis

API REST para gestionar un catálogo de vehículos, con persistencia en **MongoDB**
y caché de lecturas en **Redis**, empaquetada con Docker Compose.

## Stack

- Python 3.12 / Flask 3.1
- MongoDB 8.0 (persistencia)
- Redis 7.4 (caché con TTL)
- Docker / Docker Compose
- pytest + mongomock + fakeredis (pruebas)

## Requisitos

- Docker Desktop en ejecución (Windows, macOS o Linux).

## Puesta en marcha

```powershell
docker compose up --build -d
docker compose exec api flask --app app seed
```

La API queda disponible en `http://localhost:5000`.

## Endpoints

| Método | Ruta                | Descripción                          |
| ------ | ------------------- | ------------------------------------ |
| GET    | `/salud`            | Estado del servicio                  |
| GET    | `/vehiculos`        | Lista todos los vehículos            |
| POST   | `/vehiculos`        | Crea un vehículo (201)               |
| GET    | `/vehiculos/<id>`   | Consulta un vehículo (MongoDB/Redis) |
| PUT    | `/vehiculos/<id>`   | Actualiza parcialmente e invalida caché |
| DELETE | `/vehiculos/<id>`   | Elimina e invalida caché (204)       |

### Cuerpo de un vehículo

```json
{
  "nombre": "Auto",
  "categoria": "Terrestre (motorizado)",
  "peso_toneladas": 1.5,
  "descripcion": "Uso urbano"
}
```

Validaciones: campos exactos, texto no vacío, `peso_toneladas` numérico > 0 y
nombre único (case-insensitive).

## Política de caché (`cache_policy.py`)

- Descripción con **más de 20 caracteres** → no se cachea (`None`).
- Si no, según la longitud del `nombre`:
  - `≤ 5` caracteres → **15 s**
  - `≤ 10` caracteres → **20 s**
  - `> 10` caracteres → **40 s**

La primera lectura responde `"fuente": "mongodb"` con `cache_ttl_segundos`; las
siguientes (dentro del TTL) responden `"fuente": "redis"`. Al expirar, vuelve a MongoDB.

## Pruebas

```powershell
docker compose exec api pytest -q
```

## Estructura

```
app.py                        # factory de la app y endpoints
cache_policy.py               # reglas de TTL
seed_data.py                  # 10 vehículos de referencia
pytest.ini                    # configuración de pytest
Dockerfile / docker-compose.yml
postman/                      # colección Postman lista para importar
tests/                        # pruebas unitarias y de integración
```
