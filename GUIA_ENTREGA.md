# Guía de entrega — GitHub y video

Pasos finales para publicar el repositorio y grabar el video de demostración.

## 1. Repositorio GitHub

El repo local ya está inicializado con un commit. Solo falta crear el remoto
en GitHub y subir.

1. Crea un repositorio vacío en GitHub (sin README, sin .gitignore) llamado
   `taller-api-vehiculos`.
2. Copia la URL (HTTPS o SSH) y ejecuta desde la carpeta del proyecto:

```powershell
git remote add origin <URL_DEL_REPOSITORIO>
git branch -M main
git push -u origin main
```

Si ya tenías un `origin`, reemplázalo:

```powershell
git remote set-url origin <URL_DEL_REPOSITORIO>
git push -u origin main
```

> Nota: si es tu primer push y git pide credenciales, usa un **Personal Access
> Token** de GitHub como contraseña (Settings → Developer settings → Tokens).

## 2. Actualizar ENTREGA.txt

Rellena los marcadores y vuelve a subir:

```powershell
git add ENTREGA.txt
git commit -m "Completar datos de entrega"
git push
```

## 3. Video en YouTube (guion sugerido)

Duración objetivo: 5–8 minutos. Graba la terminal y el navegador/Postman.

1. **Presentación** (30 s): integrantes y objetivo del taller.
2. **Arquitectura** (1 min): mostrar `docker-compose.yml`, `app.py` y
   `cache_policy.py` explicando MongoDB, Redis y la regla de TTL.
3. **Levantar servicios** (1 min):
   ```powershell
   docker compose up --build -d
   docker compose ps
   docker compose exec api flask --app app seed
   ```
4. **Demostración de caché** (2 min):
   - Crear vehículo `Auto` (descripción "Uso urbano").
   - `GET` dos veces: mostrar `fuente: mongodb` y luego `fuente: redis`.
   - Esperar 16 s y repetir: vuelve a `mongodb` (expiración).
   - Crear vehículo con descripción > 20 caracteres y mostrar que no se cachea.
5. **Pruebas** (1 min): `docker compose exec api pytest -q` mostrando `7 passed`.
6. **Cierre** (30 s): conclusiones y enlaces (repo + video).

Sube el video como **No listado** o **Público** según indique el docente y
copia la URL en `ENTREGA.txt`.
