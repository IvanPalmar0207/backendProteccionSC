"""Serializer for the authenticated user's own profile."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.core.validators import validar_telefono

Usuario = get_user_model()


class PerfilSerializer(serializers.ModelSerializer):
    """Editable personal data. Email, role and document are read-only here.

    There is no endpoint that accepts a user id: the profile always resolves
    from ``request.user``, so a user can neither read nor edit someone else's
    profile. The document is an identity field: a PATCH/PUT that tries to
    change it is rejected explicitly (never silently ignored).
    """

    documento = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "email",
            "nombre_completo",
            "telefono",
            "documento",
            "direccion",
            "fecha_nacimiento",
            "role",
            "date_joined",
        )
        read_only_fields = ("id", "email", "role", "date_joined")

    def validate_telefono(self, value):
        return validar_telefono(value)

    def validate(self, attrs):
        # ``documento`` is read-only, so DRF would drop it silently. Reject any
        # attempt to change it instead of pretending the update succeeded.
        if self.instance is not None and hasattr(self, "initial_data"):
            solicitado = self.initial_data.get("documento")
            if solicitado is not None and str(solicitado) != self.instance.documento:
                raise serializers.ValidationError(
                    {"documento": "El número de documento no se puede modificar."}
                )
        return attrs
