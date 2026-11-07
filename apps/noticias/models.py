"""News model."""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Noticia(TimeStampedModel):
    titulo = models.CharField("título", max_length=200)
    resumen = models.CharField("resumen", max_length=300, blank=True)
    contenido = models.TextField("contenido")
    imagen = models.ImageField("imagen", upload_to="noticias/", null=True, blank=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="noticias",
        verbose_name="autor",
    )
    publicado = models.BooleanField("publicado", default=True)
    fecha_publicacion = models.DateTimeField("fecha de publicación", auto_now_add=True)

    class Meta:
        verbose_name = "noticia"
        verbose_name_plural = "noticias"
        ordering = ["-fecha_publicacion"]

    def __str__(self):
        return self.titulo
