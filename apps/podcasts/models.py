"""Podcast model."""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Podcast(TimeStampedModel):
    titulo = models.CharField("título", max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    audio = models.FileField("archivo de audio", upload_to="podcasts/", null=True, blank=True)
    audio_url = models.URLField("URL de audio externa", blank=True)
    duracion_segundos = models.PositiveIntegerField("duración (segundos)", null=True, blank=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="podcasts",
        verbose_name="autor",
    )
    publicado = models.BooleanField("publicado", default=True)
    fecha_publicacion = models.DateTimeField("fecha de publicación", auto_now_add=True)

    class Meta:
        verbose_name = "podcast"
        verbose_name_plural = "podcasts"
        ordering = ["-fecha_publicacion"]

    def __str__(self):
        return self.titulo

    @property
    def url_audio(self) -> str:
        """Internal file takes precedence over the external URL."""
        if self.audio:
            return self.audio.url
        return self.audio_url
