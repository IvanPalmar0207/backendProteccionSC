"""Small helper used by other apps to create notifications."""

from .models import Notificacion, TipoNotificacionChoices

ROL_ADMIN = "ADMINISTRADOR"


def notificar(usuario, titulo, mensaje="", tipo=TipoNotificacionChoices.SISTEMA, url=""):
    """Create a notification for ``usuario`` (no-op when usuario is None)."""
    if usuario is None:
        return None
    return Notificacion.objects.create(
        usuario=usuario, titulo=titulo, mensaje=mensaje, tipo=tipo, url=url
    )


def notificar_mensaje(mensaje):
    """Notify every participant of a conversation except the sender.

    The administrator is skipped even if somehow present: private chat stays
    outside the administrator's reach (S8), including its notifications.
    """
    participantes = mensaje.conversacion.participantes.exclude(pk=mensaje.remitente_id)
    for participante in participantes:
        if participante.role == ROL_ADMIN:
            continue
        notificar(
            participante,
            "Nuevo mensaje",
            f"Recibiste un mensaje en la conversación de la denuncia "
            f"{mensaje.conversacion.denuncia.identificador}.",
            tipo=TipoNotificacionChoices.MENSAJE,
            url=f"/chat/{mensaje.conversacion_id}",
        )
