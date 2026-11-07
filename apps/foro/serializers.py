from rest_framework import serializers

from .models import Publicacion, Respuesta


class RespuestaSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Respuesta
        fields = ("id", "publicacion", "contenido", "autor_nombre", "creado_en")
        read_only_fields = ("id", "publicacion", "autor_nombre", "creado_en")

    def get_autor_nombre(self, obj):
        return obj.autor.nombre_completo


class PublicacionSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()
    respuestas = RespuestaSerializer(many=True, read_only=True)
    respuestas_count = serializers.IntegerField(source="respuestas.count", read_only=True)

    class Meta:
        model = Publicacion
        fields = (
            "id",
            "titulo",
            "contenido",
            "autor_nombre",
            "respuestas",
            "respuestas_count",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("id", "autor_nombre", "respuestas", "respuestas_count", "creado_en", "actualizado_en")

    def get_autor_nombre(self, obj):
        return obj.autor.nombre_completo
