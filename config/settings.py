"""
Django settings for the Protección Inmediata SC backend.

Configuration is environment-driven (see the README's variables section). PostgreSQL is the
intended production database; SQLite is used automatically when `DB_ENGINE`
is left at its default `sqlite` value.
"""

from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
import os

from django.core.exceptions import ImproperlyConfigured

try:  # optional: only required in production (Railway provides DATABASE_URL)
    import dj_database_url

except ImportError:  # pragma: no cover - local installs may omit it
    dj_database_url = None

try:  # optional: used to serve static files in production
    import whitenoise  # noqa: F401

    HAS_WHITENOISE = True
except ImportError:  # pragma: no cover
    HAS_WHITENOISE = False

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "channels",
    "apps.core",
    "apps.usuarios",
    "apps.perfiles",
    "apps.denuncias",
    "apps.chat",
    "apps.noticias",
    "apps.podcasts",
    "apps.foro",
    "apps.notificaciones",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Serves collected static files (Django admin, DRF) in production.
    *(["whitenoise.middleware.WhiteNoiseMiddleware"] if HAS_WHITENOISE else []),
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database -------------------------------------------------------------
# Priority: DATABASE_URL (Railway/Heroku style) > DB_ENGINE=postgres > SQLite.
# SQLite stays available for local development only; production uses PostgreSQL.
DATABASE_URL = os.getenv("DATABASE_URL", "")
# Use PostgreSQL when running in production (DEBUG=False). Locally we keep
# SQLite even if DATABASE_URL is present in `.env`, so a production connection
# string never breaks local development or the test suite. Set
# USE_DATABASE_URL=True to force PostgreSQL locally if needed.
USAR_DATABASE_URL = (
    bool(DATABASE_URL)
    and dj_database_url is not None
    and (not DEBUG or env_bool("USE_DATABASE_URL", False))
)
if USAR_DATABASE_URL:
    _db = dj_database_url.config(
        default=DATABASE_URL,
        # No persistent connections: managed Postgres may sleep and close idle
        # sockets, which would surface as "server closed the connection" 500s.
        conn_max_age=0,
        ssl_require=env_bool("POSTGRES_SSL_REQUIRE", False),
    )
    _db["CONN_HEALTH_CHECKS"] = True
    DATABASES = {"default": _db}
elif os.getenv("DB_ENGINE", "sqlite").lower() == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "proteccion_inmediata"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- Authentication -------------------------------------------------------
AUTH_USER_MODEL = "usuarios.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization -------------------------------------------------
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# --- Email -----------------------------------------------------------------
# Development defaults to the console backend (the message is printed, never
# actually sent). Configure SMTP in production through environment variables.
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", "Protección Inmediata SC <no-responder@proteccioninmediata.test>"
)

# --- Password recovery -----------------------------------------------------
# Public URL of the SPA, used to build the single-use recovery link.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")
PASSWORD_RESET_TIMEOUT_MINUTES = int(os.getenv("PASSWORD_RESET_TIMEOUT_MINUTES", "30"))
# Anonymous rate limit for recovery requests, per client IP.
PASSWORD_RESET_RATE = os.getenv("PASSWORD_RESET_RATE", "5/hour")

# --- Static and media -----------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = Path(os.getenv("STATIC_ROOT") or (BASE_DIR / "staticfiles"))
MEDIA_URL = "media/"
# Uploaded files must live on a persistent volume in production (Railway
# volume mounted at MEDIA_ROOT), never on the container's ephemeral filesystem.
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT") or (BASE_DIR / "media"))
# Maximum size accepted for uploaded images (validated in apps.core.validators).
MAX_IMAGE_UPLOAD_MB = int(os.getenv("MAX_IMAGE_UPLOAD_MB", "5"))

# Media storage: filesystem by default; MEDIA_STORAGE=db keeps uploads in
# PostgreSQL (persistent in production without a container volume/account).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedStaticFilesStorage"
            if HAS_WHITENOISE
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    },
}
if os.getenv("MEDIA_STORAGE", "").strip().lower() == "db":
    STORAGES["default"] = {"BACKEND": "apps.core.storage.DatabaseStorage"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": ("rest_framework.filters.SearchFilter",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# --- CORS -----------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200"
)
CORS_ALLOW_CREDENTIALS = True

# --- Security (production behind Railway's TLS proxy) ---------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)

# --- Channels -------------------------------------------------------------
# In-memory layer keeps local development dependency-free. Set REDIS_URL to
# use a Redis channel layer (recommended for multi-process deployments).
REDIS_URL = os.getenv("REDIS_URL", "")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
elif DEBUG:
    # In-memory layer is for local development only.
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
else:
    # Never silently fall back to memory in production.
    raise ImproperlyConfigured(
        "REDIS_URL es obligatorio en producción: no se permite el channel layer en memoria."
    )
