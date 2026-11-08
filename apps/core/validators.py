"""Shared field validators.

The frontend validates too, but the backend is the real boundary: uploaded
files and external links are re-checked here.
"""

import re
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}
MIME_IMAGEN = {"image/jpeg", "image/png", "image/webp"}

# Colombian phone: digits only, 7 to 10 of them (optional field).
TELEFONO_PATTERN = re.compile(r"^[0-9]{7,10}$")


EDAD_MINIMA_NACIMIENTO = 10


def validar_fecha_sucesos(valor):
    """The date something happened can never be in the future.

    Optional field (``None`` allowed). Uses the project's local date so the
    boundary respects ``TIME_ZONE``.
    """
    if valor in (None, ""):
        return valor
    if valor > timezone.localdate():
        raise ValidationError(
            "La fecha de los sucesos no puede ser posterior al día de hoy."
        )
    return valor


def validar_fecha_nacimiento(valor):
    """Reject future dates and people younger than the minimum age.

    The birth date is optional (``None``/empty is allowed). Age is computed in
    completed years against the server's current date, so it accounts for the
    day and month (and leap years) instead of a hardcoded date.
    """
    if valor in (None, ""):
        return valor
    hoy = date.today()
    if valor > hoy:
        raise ValidationError("La fecha de nacimiento no puede ser futura.")
    edad = hoy.year - valor.year - ((hoy.month, hoy.day) < (valor.month, valor.day))
    if edad < EDAD_MINIMA_NACIMIENTO:
        raise ValidationError(
            "La persona debe tener al menos 10 años para registrarse."
        )
    return valor


def validar_telefono(valor) -> str:
    """Reject letters, spaces and symbols; keep the value as a digit string."""
    if valor in (None, ""):
        return ""
    texto = str(valor)
    if not TELEFONO_PATTERN.match(texto):
        raise ValidationError(
            "El teléfono debe contener solo números (entre 7 y 10 dígitos)."
        )
    return texto


def validar_enlace_https(valor: str) -> None:
    """Only secure external links are accepted."""
    if not valor.lower().startswith("https://"):
        raise ValidationError("El enlace debe comenzar con https://")


def validar_imagen(archivo) -> None:
    """Validate an uploaded image by extension, MIME type, size and content.

    Added on top of ``ImageField`` so a renamed executable or an oversized file
    never reaches storage.
    """
    nombre = (getattr(archivo, "name", "") or "").lower()
    if not any(nombre.endswith(ext) for ext in EXTENSIONES_IMAGEN):
        raise ValidationError(
            "Formato no permitido. Usá JPG, PNG o WEBP."
        )

    content_type = getattr(archivo, "content_type", "") or ""
    if content_type and content_type not in MIME_IMAGEN:
        raise ValidationError("El tipo de archivo no corresponde a una imagen válida.")

    limite_mb = getattr(settings, "MAX_IMAGE_UPLOAD_MB", 5)
    if archivo.size and archivo.size > limite_mb * 1024 * 1024:
        raise ValidationError(f"La imagen supera el tamaño máximo de {limite_mb} MB.")

    # Verify the actual bytes are a decodable image (defends against a
    # renamed payload). Pillow invalidates the stream, so rewind afterwards.
    try:
        imagen = Image.open(archivo)
        imagen.verify()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValidationError("El archivo no es una imagen válida.") from error
    finally:
        if hasattr(archivo, "seek"):
            archivo.seek(0)
