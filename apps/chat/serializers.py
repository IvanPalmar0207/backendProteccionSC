"""Chat serializers.

Participant names are operational data: a professional and the report owner
share the thread. For anonymous reports the reporter is rendered as
``Denunciante anónimo`` to everyone except the reporter themselves, so the chat
never bypasses the identity protection of ``apps.denuncias`` (S5, Fase 8).
"""

from rest_framework import serializers

from .models import Conversacion, Mensaje

ANONIMO = "Denunciante anónimo"


def _viewer_id(context) -> int | None:
    request = context.get("request")
    return getattr(getattr(request, "user", None), "id", None)


def _nombre_visible(denuncia, usuario, viewer_id: int | None) -> str:
    if (
        denuncia.es_anonima
        and usuario.id == denuncia.denunciante_id
        and viewer_id != usuario.id
    ):
        return ANONIMO
    return usuario.nombre_completo


class ParticipanteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre_completo = serializers.CharField()
    role = serializers.CharField()


class MensajeSerializer(serializers.ModelSerializer):
    remitente = serializers.SerializerMethodField()

    class Meta:
        model = Mensaje
        fields = ("id", "remitente", "contenido", "leido", "creado_en")

    def get_remitente(self, obj):
        usuario = obj.remitente
        return {
            "id": usuario.id,
            "nombre_completo": _nombre_visible(
                obj.conversacion.denuncia, usuario, _viewer_id(self.context)
            ),
            "role": usuario.role,
        }


class ConversacionSerializer(serializers.ModelSerializer):
    denuncia = serializers.SerializerMethodField()
    participantes = serializers.SerializerMethodField()
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

    def get_participantes(self, obj):
        """Authorized participants: the reporter and the *current* assignee.

        Computed from the report instead of the legacy M2M, so a reassignment
        never leaves a stale (previously assigned) professional as participant.
        """
        viewer_id = _viewer_id(self.context)
        denuncia = obj.denuncia
        usuarios = [denuncia.denunciante]
        if denuncia.profesional_asignado_id:
            usuarios.append(denuncia.profesional_asignado)
        return [
            {
                "id": usuario.id,
                "nombre_completo": _nombre_visible(denuncia, usuario, viewer_id),
                "role": usuario.role,
            }
            for usuario in usuarios
        ]

    def get_ultimo_mensaje(self, obj):
        ultimo = obj.mensajes.order_by("-creado_en").first()
        if ultimo is None:
            return None
        return {
            "contenido": ultimo.contenido,
            "remitente_nombre": _nombre_visible(
                obj.denuncia, ultimo.remitente, _viewer_id(self.context)
            ),
            "creado_en": ultimo.creado_en,
        }

    def get_no_leidos(self, obj):
        request = self.context.get("request")
        if request is None:
            return 0
        return obj.mensajes.filter(leido=False).exclude(remitente=request.user).count()


class CrearConversacionSerializer(serializers.Serializer):
    denuncia = serializers.IntegerField()
