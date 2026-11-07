"""Serializer for the authenticated user's own profile."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

Usuario = get_user_model()


class PerfilSerializer(serializers.ModelSerializer):
    """Editable personal data. Email and role are read-only here.

    There is no endpoint that accepts a user id: the profile always resolves
    from ``request.user``, so a user can neither read nor edit someone else's
    profile.
    """

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
