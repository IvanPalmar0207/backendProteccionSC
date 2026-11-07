"""Serializers for reports.

Two clearly separated read serializers exist:

* ``DenunciaUsuarioSerializer`` — for the owner (uses ``request.user``).
* ``DenunciaProfesionalSerializer`` — for professionals and the attention
  module. Its ``solicitante`` field is ``None`` for anonymous reports, so the
  identity keys are never serialized for those cases.

No serializer exposes the author's identity to a professional when the report
is anonymous.
"""

from rest_framework import serializers

from .models import Denuncia, EstadoChoices, SeguimientoDenuncia


class SeguimientoSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()

    class Meta:
        model = SeguimientoDenuncia
        fields = (
            "id",
            "estado_anterior",
            "estado_nuevo",
            "observacion",
            "autor_nombre",
            "creado_en",
        )

    def get_autor_nombre(self, obj):
        if obj.autor is None:
            return "Sistema"
        # A professional's name is operational data, never the reporter identity.
        return obj.autor.nombre_completo


class DenunciaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Denuncia
        fields = (
            "modalidad",
            "tipo_situacion",
            "descripcion",
            "ubicacion",
            "fecha_hechos",
        )

    def validate_descripcion(self, value):
        value = (value or "").strip()
        if len(value) < 10:
            raise serializers.ValidationError(
                "La descripción debe tener al menos 10 caracteres."
            )
        return value


class DenunciaUsuarioSerializer(serializers.ModelSerializer):
    """Owner-facing serializer. The owner always sees their own report."""

    identificador = serializers.CharField(read_only=True)
    es_anonima = serializers.BooleanField(read_only=True)
    profesional_asignado = serializers.SerializerMethodField()
    seguimientos = SeguimientoSerializer(many=True, read_only=True)

    class Meta:
        model = Denuncia
        fields = (
            "id",
            "identificador",
            "modalidad",
            "es_anonima",
            "tipo_situacion",
            "descripcion",
            "ubicacion",
            "fecha_hechos",
            "estado",
            "profesional_asignado",
            "seguimientos",
            "creado_en",
            "actualizado_en",
        )

    def get_profesional_asignado(self, obj):
        if obj.profesional_asignado_id is None:
            return None
        return {
            "id": obj.profesional_asignado_id,
            "nombre_completo": obj.profesional_asignado.nombre_completo,
        }


class DenunciaProfesionalSerializer(serializers.ModelSerializer):
    """Professional/attention serializer.

    ``solicitante`` deliberately returns ``None`` for anonymous reports. Only
    the modality is visible, never the name, email, phone or document.
    """

    identificador = serializers.CharField(read_only=True)
    es_anonima = serializers.BooleanField(read_only=True)
    solicitante = serializers.SerializerMethodField()
    profesional_asignado = serializers.SerializerMethodField()
    seguimientos = SeguimientoSerializer(many=True, read_only=True)

    class Meta:
        model = Denuncia
        fields = (
            "id",
            "identificador",
            "modalidad",
            "es_anonima",
            "tipo_situacion",
            "descripcion",
            "ubicacion",
            "fecha_hechos",
            "estado",
            "solicitante",
            "profesional_asignado",
            "seguimientos",
            "creado_en",
            "actualizado_en",
        )

    def get_solicitante(self, obj):
        if obj.es_anonima:
            return None
        autor = obj.denunciante
        return {
            "nombre_completo": autor.nombre_completo,
            "email": autor.email,
            "telefono": autor.telefono,
            "documento": autor.documento,
        }

    def get_profesional_asignado(self, obj):
        if obj.profesional_asignado_id is None:
            return None
        return {
            "id": obj.profesional_asignado_id,
            "nombre_completo": obj.profesional_asignado.nombre_completo,
        }


class DenunciaEstadoUpdateSerializer(serializers.Serializer):
    """Validated payload for the professional state transition endpoint."""

    estado = serializers.ChoiceField(choices=EstadoChoices.choices)
    observacion = serializers.CharField(required=False, allow_blank=True, default="")
