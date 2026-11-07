"""Notification serializers."""

from rest_framework import serializers

from .models import Notificacion


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ("id", "titulo", "mensaje", "tipo", "url", "leida", "creado_en")
        read_only_fields = ("id", "titulo", "mensaje", "tipo", "url", "creado_en")
