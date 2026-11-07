from rest_framework import serializers

from .models import Podcast, PlataformaChoices


class PodcastSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()
    plataforma_etiqueta = serializers.SerializerMethodField()

    class Meta:
        model = Podcast
        fields = (
            "id",
            "titulo",
            "descripcion",
            "programa",
            "plataforma",
            "plataforma_etiqueta",
            "enlace",
            "portada",
            "autor_nombre",
            "publicado",
            "fecha_publicacion",
        )
        read_only_fields = ("id", "autor_nombre", "plataforma_etiqueta")
        extra_kwargs = {
            # `portada` is optional and may be cleared by sending null.
            "portada": {"required": False, "allow_null": True},
            "enlace": {"required": True, "allow_blank": False},
        }

    def get_autor_nombre(self, obj):
        return obj.autor.nombre_completo if obj.autor else "Protección Inmediata SC"

    def get_plataforma_etiqueta(self, obj):
        return PlataformaChoices(obj.plataforma).label

    def _eliminar_portada_anterior(self, instance, portada_nueva):
        if instance.portada and instance.portada != portada_nueva:
            instance.portada.delete(save=False)

    def update(self, instance, validated_data):
        if "portada" in validated_data:
            self._eliminar_portada_anterior(instance, validated_data.get("portada"))
        return super().update(instance, validated_data)
