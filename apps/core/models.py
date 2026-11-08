"""Shared abstract models and DB-backed media storage."""

from django.db import models


class StoredFile(models.Model):
    """Binary media kept in the database.

    Lets uploaded images persist in production without a container volume or an
    external object-storage account (the PostgreSQL instance already has a
    persistent volume).
    """

    name = models.CharField("nombre", max_length=255, unique=True)
    content = models.BinaryField("contenido")
    content_type = models.CharField("tipo", max_length=120, blank=True)
    size = models.PositiveBigIntegerField("tamaño", default=0)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "archivo almacenado"
        verbose_name_plural = "archivos almacenados"

    def __str__(self):
        return self.name


class TimeStampedModel(models.Model):
    """Adds creation/update timestamps to any model."""

    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        abstract = True
