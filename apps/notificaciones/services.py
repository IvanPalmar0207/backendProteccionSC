"""Small helper used by other apps to create notifications."""

from .models import Notificacion, TipoNotificacionChoices


def notificar(usuario, titulo, mensaje="", tipo=TipoNotificacionChoices.SISTEMA, url=""):
    """Create a notification for ``usuario`` (no-op when usuario is None)."""
    if usuario is None:
        return None
    return Notificacion.objects.create(
        usuario=usuario, titulo=titulo, mensaje=mensaje, tipo=tipo, url=url
    )
