"""News model with editorial category and a validated cover image."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.core.validators import validar_imagen


class CategoriaNoticiaChoices(models.TextChoices):
    PREVENCION = "PREVENCION", "Prevención"
    ACOMPANAMIENTO = "ACOMPANAMIENTO", "Acompañamiento"
    DERECHOS = "DERECHOS", "Derechos y rutas"
    COMUNIDAD = "COMUNIDAD", "Comunidad"
    INSTITUCIONAL = "INSTITUCIONAL", "Institucional"


class Noticia(TimeStampedModel):
    titulo = models.CharField("título", max_length=200)
    resumen = models.CharField("resumen", max_length=300, blank=True)
    contenido = models.TextField("contenido")
    categoria = models.CharField(
        "categoría",
        max_length=20,
        choices=CategoriaNoticiaChoices.choices,
        default=CategoriaNoticiaChoices.INSTITUCIONAL,
    )
    imagen = models.ImageField(
        "imagen de portada",
        upload_to="noticias/portadas/",
        null=True,
        blank=True,
        validators=[validar_imagen],
    )
    destacada = models.BooleanField("destacada", default=False)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="noticias",
        verbose_name="autor",
    )
    publicado = models.BooleanField("publicado", default=True)
    fecha_publicacion = models.DateTimeField("fecha de publicación", default=timezone.now)

    class Meta:
        verbose_name = "noticia"
        verbose_name_plural = "noticias"
        ordering = ["-destacada", "-fecha_publicacion"]

    def __str__(self):
        return self.titulo
