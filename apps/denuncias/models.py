"""Report (denuncia) and follow-up models.

Anonymity model
---------------
Every report keeps a hard internal link to its author (``denunciante``) so the
owner can follow up. Identity is *never* sent to professionals through the API:
the professional-facing serializer renders ``solicitante`` as ``null`` for
anonymous reports (see ``serializers.py``). The split is enforced by the
serializer, not by the client.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class ModalidadChoices(models.TextChoices):
    PUBLICA = "PUBLICA", "Pública"
    ANONIMA = "ANONIMA", "Anónima"


class EstadoChoices(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_PROCESO = "EN_PROCESO", "En proceso"
    FINALIZADA = "FINALIZADA", "Finalizada"


class TipoSituacionChoices(models.TextChoices):
    VIOLENCIA_INTRAFAMILIAR = "VIOLENCIA_INTRAFAMILIAR", "Violencia intrafamiliar"
    ABUSO = "ABUSO", "Abuso"
    ACOSO = "ACOSO", "Acoso"
    OTRO = "OTRO", "Otro"


class Denuncia(TimeStampedModel):
    """A report of violence, abuse or harassment."""

    codigo = models.UUIDField(
        "código", default=uuid.uuid4, editable=False, unique=True
    )
    denunciante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="denuncias",
        verbose_name="denunciante",
    )
    modalidad = models.CharField(
        "modalidad", max_length=10, choices=ModalidadChoices.choices
    )
    tipo_situacion = models.CharField(
        "tipo de situación",
        max_length=30,
        choices=TipoSituacionChoices.choices,
        default=TipoSituacionChoices.OTRO,
    )
    descripcion = models.TextField("descripción de los hechos")
    ubicacion = models.CharField("ubicación", max_length=200, blank=True)
    fecha_hechos = models.DateField("fecha de los hechos", null=True, blank=True)
    estado = models.CharField(
        "estado", max_length=15, choices=EstadoChoices.choices, default=EstadoChoices.PENDIENTE
    )
    profesional_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="denuncias_asignadas",
        verbose_name="profesional asignado",
        limit_choices_to={"role": "PROFESIONAL"},
    )

    class Meta:
        verbose_name = "denuncia"
        verbose_name_plural = "denuncias"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.identificador} ({self.modalidad})"

    @property
    def es_anonima(self) -> bool:
        return self.modalidad == ModalidadChoices.ANONIMA

    @property
    def identificador(self) -> str:
        """Short human-friendly identifier derived from the UUID."""
        return str(self.codigo).split("-")[0].upper()


class SeguimientoDenuncia(TimeStampedModel):
    """Immutable log entry describing a state change or an observation."""

    denuncia = models.ForeignKey(
        Denuncia, on_delete=models.CASCADE, related_name="seguimientos"
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seguimientos_realizados",
    )
    estado_anterior = models.CharField(
        "estado anterior", max_length=15, choices=EstadoChoices.choices, blank=True
    )
    estado_nuevo = models.CharField(
        "estado nuevo", max_length=15, choices=EstadoChoices.choices, blank=True
    )
    observacion = models.TextField("observación", blank=True)

    class Meta:
        verbose_name = "seguimiento de denuncia"
        verbose_name_plural = "seguimientos de denuncias"
        ordering = ["creado_en"]

    def __str__(self):
        return f"Seguimiento {self.denuncia.identificador}: {self.estado_anterior} -> {self.estado_nuevo}"
