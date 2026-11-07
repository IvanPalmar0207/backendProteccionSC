"""Shared abstract models."""

from django.db import models


class TimeStampedModel(models.Model):
    """Adds creation/update timestamps to any model."""

    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        abstract = True
