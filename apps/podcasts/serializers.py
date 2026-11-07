from rest_framework import serializers

from .models import Podcast


class PodcastSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()
    url_audio = serializers.SerializerMethodField()

    class Meta:
        model = Podcast
        fields = (
            "id",
            "titulo",
            "descripcion",
            "audio",
            "audio_url",
            "url_audio",
            "duracion_segundos",
            "autor_nombre",
            "publicado",
            "fecha_publicacion",
        )
        read_only_fields = ("id", "autor_nombre", "url_audio", "fecha_publicacion")

    def get_autor_nombre(self, obj):
        return obj.autor.nombre_completo if obj.autor else "Protección Inmediata SC"

    def get_url_audio(self, obj):
        url = obj.url_audio
        if not url:
            return ""
        request = self.context.get("request")
        if request is not None and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url
