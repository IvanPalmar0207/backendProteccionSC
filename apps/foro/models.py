"""Forum models: publications and their replies."""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Publicacion(TimeStampedModel):
    titulo = models.CharField("título", max_length=200)
    contenido = models.TextField("contenido")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="publicaciones_foro",
        verbose_name="autor",
    )

    class Meta:
        verbose_name = "publicación del foro"
        verbose_name_plural = "publicaciones del foro"
        ordering = ["-creado_en"]

    def __str__(self):
        return self.titulo


class Respuesta(TimeStampedModel):
    publicacion = models.ForeignKey(
        Publicacion,
        on_delete=models.CASCADE,
        related_name="respuestas",
        verbose_name="publicación",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="respuestas_foro",
        verbose_name="autor",
    )
    contenido = models.TextField("contenido")

    class Meta:
        verbose_name = "respuesta del foro"
        verbose_name_plural = "respuestas del foro"
        ordering = ["creado_en"]

    def __str__(self):
        return f"Respuesta de {self.autor_id}"
