from rest_framework import serializers

from .models import CategoriaNoticiaChoices, Noticia


class NoticiaSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()
    categoria_etiqueta = serializers.SerializerMethodField()

    class Meta:
        model = Noticia
        fields = (
            "id",
            "titulo",
            "resumen",
            "contenido",
            "categoria",
            "categoria_etiqueta",
            "imagen",
            "destacada",
            "autor_nombre",
            "publicado",
            "fecha_publicacion",
        )
        read_only_fields = ("id", "autor_nombre", "categoria_etiqueta")
        extra_kwargs = {
            # The cover image is optional and may be cleared by sending null.
            "imagen": {"required": False, "allow_null": True},
        }

    def get_autor_nombre(self, obj):
        return obj.autor.nombre_completo if obj.autor else "Protección Inmediata SC"

    def get_categoria_etiqueta(self, obj):
        return CategoriaNoticiaChoices(obj.categoria).label

    def _eliminar_imagen_anterior(self, instance, imagen_nueva):
        if instance.imagen and instance.imagen != imagen_nueva:
            instance.imagen.delete(save=False)

    def update(self, instance, validated_data):
        if "imagen" in validated_data:
            self._eliminar_imagen_anterior(instance, validated_data.get("imagen"))
        return super().update(instance, validated_data)
