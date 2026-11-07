"""Podcast model.

Episodes are hosted externally (Spotify, YouTube, Apple Podcasts, ...): the
platform stores a validated HTTPS link and an optional cover image, never the
audio itself. There is no custom player and no audio upload.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.core.validators import validar_enlace_https, validar_imagen


class PlataformaChoices(models.TextChoices):
    SPOTIFY = "SPOTIFY", "Spotify"
    YOUTUBE = "YOUTUBE", "YouTube"
    APPLE_PODCASTS = "APPLE_PODCASTS", "Apple Podcasts"
    OTRA = "OTRA", "Otra"


class Podcast(TimeStampedModel):
    titulo = models.CharField("título", max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    programa = models.CharField("programa", max_length=150, blank=True)
    plataforma = models.CharField(
        "plataforma",
        max_length=20,
        choices=PlataformaChoices.choices,
        default=PlataformaChoices.OTRA,
    )
    enlace = models.URLField(
        "enlace del episodio",
        max_length=500,
        validators=[validar_enlace_https],
        help_text="URL HTTPS del episodio en su plataforma de origen.",
    )
    portada = models.ImageField(
        "portada",
        upload_to="podcasts/portadas/",
        null=True,
        blank=True,
        validators=[validar_imagen],
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="podcasts",
        verbose_name="autor",
    )
    publicado = models.BooleanField("publicado", default=True)
    fecha_publicacion = models.DateTimeField("fecha de publicación", default=timezone.now)

    class Meta:
        verbose_name = "pódcast"
        verbose_name_plural = "pódcasts"
        ordering = ["-fecha_publicacion"]

    def __str__(self):
        return self.titulo
