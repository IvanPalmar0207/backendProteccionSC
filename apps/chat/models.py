"""Conversation and message models.

The chat is private: only the conversation participants may read or write.
The administrator has no special access (see ``permissions.py`` and the
consumer), which is why ``Mensaje`` is deliberately not registered in the
Django admin.
"""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Conversacion(TimeStampedModel):
    """One private thread, always anchored to a report."""

    denuncia = models.ForeignKey(
        "denuncias.Denuncia",
        on_delete=models.CASCADE,
        related_name="conversaciones",
        verbose_name="denuncia",
    )
    participantes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="conversaciones",
        verbose_name="participantes",
    )

    class Meta:
        verbose_name = "conversación"
        verbose_name_plural = "conversaciones"
        ordering = ["-actualizado_en"]

    def __str__(self):
        return f"Conversación de {self.denuncia.identificador}"

    def es_participante(self, usuario) -> bool:
        if not usuario or not usuario.is_authenticated:
            return False
        return self.participantes.filter(pk=usuario.pk).exists()

    def acceso_permitido(self, usuario) -> bool:
        """Only the reporter or the professional currently assigned.

        The administrator is always denied (private chats stay private), and a
        professional loses access as soon as the case is reassigned.
        """
        if not usuario or not usuario.is_authenticated:
            return False
        if usuario.role == "ADMINISTRADOR":
            return False
        denuncia = self.denuncia
        if denuncia.denunciante_id == usuario.id:
            return True
        return denuncia.profesional_asignado_id == usuario.id


class Mensaje(TimeStampedModel):
    """A persisted chat message."""

    conversacion = models.ForeignKey(
        Conversacion,
        on_delete=models.CASCADE,
        related_name="mensajes",
        verbose_name="conversación",
    )
    remitente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mensajes_enviados",
        verbose_name="remitente",
    )
    contenido = models.TextField("contenido")
    leido = models.BooleanField("leído", default=False)

    class Meta:
        verbose_name = "mensaje"
        verbose_name_plural = "mensajes"
        ordering = ["creado_en"]

    def __str__(self):
        return f"{self.remitente_id}: {self.contenido[:30]}"
