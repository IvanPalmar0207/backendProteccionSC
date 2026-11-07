"""Internal notification model."""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class TipoNotificacionChoices(models.TextChoices):
    DENUNCIA = "DENUNCIA", "Denuncia"
    ESTADO = "ESTADO", "Cambio de estado"
    MENSAJE = "MENSAJE", "Mensaje"
    SISTEMA = "SISTEMA", "Sistema"


class Notificacion(TimeStampedModel):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones",
    )
    titulo = models.CharField("título", max_length=150)
    mensaje = models.TextField("mensaje", blank=True)
    tipo = models.CharField(
        "tipo",
        max_length=15,
        choices=TipoNotificacionChoices.choices,
        default=TipoNotificacionChoices.SISTEMA,
    )
    url = models.CharField("enlace", max_length=255, blank=True)
    leida = models.BooleanField("leída", default=False)

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.usuario.email}: {self.titulo}"
