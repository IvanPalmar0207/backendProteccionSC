"""Chat serializers.

Participant names are operational data: a professional and the report owner
share the thread. The reporter's identity is never added here (anonymous
reports stay anonymous even inside the chat serializer).
"""

from rest_framework import serializers

from .models import Conversacion, Mensaje


class ParticipanteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre_completo = serializers.CharField()
    role = serializers.CharField()


class MensajeSerializer(serializers.ModelSerializer):
    remitente = ParticipanteSerializer(read_only=True)

    class Meta:
        model = Mensaje
        fields = ("id", "remitente", "contenido", "leido", "creado_en")


class ConversacionSerializer(serializers.ModelSerializer):
    denuncia = serializers.SerializerMethodField()
    participantes = ParticipanteSerializer(many=True, read_only=True)
    ultimo_mensaje = serializers.SerializerMethodField()
    no_leidos = serializers.SerializerMethodField()

    class Meta:
        model = Conversacion
        fields = (
            "id",
            "denuncia",
            "participantes",
            "ultimo_mensaje",
            "no_leidos",
            "creado_en",
            "actualizado_en",
        )

    def get_denuncia(self, obj):
        denuncia = obj.denuncia
        return {
            "id": denuncia.id,
            "identificador": denuncia.identificador,
            "modalidad": denuncia.modalidad,
            "es_anonima": denuncia.es_anonima,
            "estado": denuncia.estado,
        }

    def get_ultimo_mensaje(self, obj):
        ultimo = obj.mensajes.order_by("-creado_en").first()
        if ultimo is None:
            return None
        return {
            "contenido": ultimo.contenido,
            "remitente_nombre": ultimo.remitente.nombre_completo,
            "creado_en": ultimo.creado_en,
        }

    def get_no_leidos(self, obj):
        request = self.context.get("request")
        if request is None:
            return 0
        return obj.mensajes.filter(leido=False).exclude(remitente=request.user).count()


class CrearConversacionSerializer(serializers.Serializer):
    denuncia = serializers.IntegerField()
