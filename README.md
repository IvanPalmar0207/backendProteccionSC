# Protección Inmediata SC — Backend

API REST + WebSocket de la plataforma **Protección Inmediata SC**, construida con
**Django + Django REST Framework + Django Channels**.

Este repositorio (`backendProteccionSC`) contiene únicamente el servidor. El cliente Angular
vive en el repositorio hermano **`frontendProteccionSC`** (`../frontEnd`).
La documentación funcional/global del proyecto está en el `README.md` de la raíz del workspace.

---

## Requisitos

- Python 3.14+
- SQLite (desarrollo local, por defecto) o PostgreSQL (producción)
- Redis (opcional; solo si se usa un channel layer distribuido en producción)

## Instalación y ejecución

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux/macOS

pip install -r requirements.txt

copy .env.example .env            # Windows  (cp en Linux/macOS)  ← y completar valores
python manage.py migrate
python manage.py seed_demo        # datos de demostración idempotentes
python manage.py runserver        # API en http://localhost:8000
```

## Configuración (variables de entorno)

Toda la configuración vive en `.env` (plantilla: `.env.example`). **`.env` está ignorado por
Git y nunca debe versionarse.** Variables principales: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`,
`DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DB_ENGINE`/`POSTGRES_*`, `JWT_*`, `REDIS_URL`,
`EMAIL_*`, `FRONTEND_URL`, `PASSWORD_RESET_*`, `MAX_IMAGE_UPLOAD_MB`.

## Estructura del proyecto

```
backend/
├─ manage.py
├─ requirements.txt
├─ .env.example              # plantilla (el .env real está ignorado)
├─ config/                   # proyecto Django
│  ├─ settings.py            # configuración (lee variables de entorno)
│  ├─ urls.py                # raíz de rutas (admin + /api + websocket)
│  ├─ asgi.py                # ASGI: HTTP + Channels/WebSocket
│  └─ wsgi.py
└─ apps/                     # aplicaciones separadas por dominio
   ├─ core/                  # modelos base, permisos por rol, validadores,
   │                         # excepciones (409), paginación y throttling
   ├─ usuarios/              # Usuario custom, registro, JWT, recuperación de contraseña,
   │                         # administración de cuentas
   ├─ perfiles/              # perfil propio (lectura/edición)
   ├─ denuncias/             # denuncias, seguimiento, asignación de profesionales
   ├─ chat/                  # conversaciones y mensajes (REST + WebSocket)
   ├─ noticias/              # noticias y categorías (CRUD admin, lectura pública)
   ├─ podcasts/              # pódcast por enlace externo (sin audio)
   ├─ foro/                  # publicaciones y respuestas
   └─ notificaciones/        # notificaciones internas por usuario
```

Cada app es autocontenida: `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`
y su carpeta `tests/`.

## Modelo de roles y permisos

Tres roles exclusivos (`Usuario.role`): **USUARIO**, **PROFESIONAL**, **ADMINISTRADOR**.
Los permisos reutilizables viven en `apps/core/permissions.py` (`IsUsuario`, `IsProfesional`,
`IsAdministrador`, `IsOwnerOrReadOnly`), sin bypass de superusuario.

Puntos garantizados desde el backend (no solo en el cliente):

- **Aislamiento de denuncias**: el usuario solo ve las suyas; el profesional **solo** las que
  tiene asignadas; el administrador supervisa sin ver la identidad de denunciantes anónimos.
- **Asignación automática** de un profesional activo con menos casos al registrar una denuncia
  (transaccional); si no hay profesionales, queda pendiente de asignación.
- **Chat privado**: solo el denunciante y el profesional **actualmente asignado** (REST y
  WebSocket); el administrador nunca accede. Los cambios de asignación revocan el acceso.
- **Denuncia completada** (`FINALIZADA`): solo lectura; las escrituras responden `409 Conflict`.
- **Campos de identidad inmutables** (`documento`, correo) y validaciones de teléfono y
  fecha de nacimiento (edad mínima 10 años) / fecha de sucesos (no futura).

## API (resumen)

Prefijo: `/api/`

- `auth/`: `register/`, `login/`, `refresh/`, `me/`, `password-reset/*`, `usuarios/` (admin).
- `perfiles/mi-perfil/`: perfil propio.
- `denuncias/mis-denuncias/` (dueño), `denuncias/profesional/` (solo asignadas),
  `denuncias/admin/` (supervisión y asignación manual).
- `chat/conversaciones/` (+ `/mensajes/`, `/marcar_leidos/`).
- `noticias/`, `podcasts/`, `foro/publicaciones/` (+ `/responder/`), `notificaciones/`.
- WebSocket: `/ws/chat/<conversacion_id>/?token=<access>` (autenticado por JWT).

## Pruebas

```bash
python manage.py test apps          # suite completa
python manage.py test apps.denuncias # app puntual
python manage.py makemigrations --check --dry-run
```

## Seguridad

- `.env`, `db.sqlite3`, `media/`, `.venv/` y artefactos están en `.gitignore`.
- No se versionan credenciales ni secretos; solo `.env.example` como plantilla.
- Los datos de demostración (`seed_demo`) son ficticios.
- La identidad de denunciantes anónimos nunca se expone por API ni por WebSocket.

## Frontend (repositorio hermano)

El cliente Angular (`frontendProteccionSC`) consume esta API en `http://localhost:8000/api`
y el WebSocket en `ws://localhost:8000`. Su estructura (`core/`, `features/`, `shared/`,
`styles/`) se documenta en su propio `README.md`.
