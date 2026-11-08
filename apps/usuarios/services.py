"""Password recovery services.

Security properties:
- The raw token never touches the database: only its SHA-256 hash is stored.
- Tokens expire (``PASSWORD_RESET_TIMEOUT_MINUTES``) and are single use.
- Previously issued refresh tokens are blacklisted after a successful reset.
- Requesting a link returns a generic answer regardless of whether the email
  exists, preventing account enumeration.
"""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import TokenRecuperacion, Usuario


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def crear_token_recuperacion(usuario: Usuario) -> str:
    """Create a fresh recovery token, invalidating previous unused ones."""
    TokenRecuperacion.objects.filter(usuario=usuario, usado=False).update(usado=True)

    raw_token = secrets.token_urlsafe(32)
    TokenRecuperacion.objects.create(
        usuario=usuario,
        token_hash=_hash_token(raw_token),
        expira_en=timezone.now() + timedelta(minutes=settings.PASSWORD_RESET_TIMEOUT_MINUTES),
    )
    return raw_token


def buscar_token(token: str) -> TokenRecuperacion | None:
    if not token:
        return None
    return TokenRecuperacion.objects.filter(token_hash=_hash_token(token)).first()


def token_es_valido(token: str) -> bool:
    registro = buscar_token(token)
    return bool(registro and registro.vigente)


def enviar_correo_recuperacion(usuario: Usuario, raw_token: str) -> None:
    """Send the recovery link. Raises on real delivery failures."""
    enlace = f"{settings.FRONTEND_URL}/restablecer?token={raw_token}"
    minutos = settings.PASSWORD_RESET_TIMEOUT_MINUTES
    asunto = "Recuperación de contraseña · Protección Inmediata SC"
    mensaje = (
        "Recibimos una solicitud para restablecer la contraseña de tu cuenta.\n\n"
        f"Abre este enlace para crear una nueva contraseña:\n{enlace}\n\n"
        f"El enlace vence en {minutos} minutos y sólo puede usarse una vez.\n"
        "Si no solicitaste el cambio, puedes ignorar este correo."
    )
    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [usuario.email],
        fail_silently=False,
    )


def invalidar_tokens_refresh(usuario: Usuario) -> int:
    """Blacklist every outstanding refresh token belonging to the user."""
    blacklisted = 0
    for token in OutstandingToken.objects.filter(user=usuario):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        if created:
            blacklisted += 1
    return blacklisted


def consumir_token(registro: TokenRecuperacion, nueva_password: str) -> int:
    """Apply the new password, burn the token and revoke refresh tokens."""
    registro.usado = True
    registro.save(update_fields=["usado"])

    usuario = registro.usuario
    usuario.set_password(nueva_password)
    usuario.save(update_fields=["password"])
    return invalidar_tokens_refresh(usuario)
