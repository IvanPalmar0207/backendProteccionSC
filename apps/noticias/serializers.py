from rest_framework import serializers

from .models import Noticia


class NoticiaSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Noticia
        fields = (
            "id",
            "titulo",
            "resumen",
            "contenido",
            "imagen",
            "autor_nombre",
            "publicado",
            "fecha_publicacion",
        )
        read_only_fields = ("id", "autor_nombre", "fecha_publicacion")

    def get_autor_nombre(self, obj):
        return obj.autor.nombre_completo if obj.autor else "Protección Inmediata SC"
