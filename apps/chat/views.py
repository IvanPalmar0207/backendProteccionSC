"""Chat REST endpoints.

List is filtered to the caller's conversations; detail and actions rely on the
object-level ``EsParticipanteDeConversacion`` permission, so a non-participant
(including an administrator) receives 403.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.denuncias.models import Denuncia
from apps.denuncias.services import asegurar_editable
from apps.notificaciones.services import notificar_mensaje

from .models import Conversacion, Mensaje
from .permissions import EsParticipanteDeConversacion
from .serializers import (
    ConversacionSerializer,
    MensajeSerializer,
)

Usuario = get_user_model()

ROL_ADMIN = "ADMINISTRADOR"
ROL_PROFESIONAL = "PROFESIONAL"


def _serializar_mensaje(mensaje: Mensaje) -> dict:
    return {
        "id": mensaje.id,
        "remitente": {
            "id": mensaje.remitente_id,
            "nombre_completo": mensaje.remitente.nombre_completo,
            "role": mensaje.remitente.role,
        },
        "contenido": mensaje.contenido,
        "leido": mensaje.leido,
        "creado_en": mensaje.creado_en.isoformat(),
    }


def broadcast_mensaje(mensaje: Mensaje) -> None:
    """Push a persisted message to every WebSocket in the conversation group."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"chat_{mensaje.conversacion_id}",
        {"type": "chat.message", "mensaje": _serializar_mensaje(mensaje)},
    )


class ConversacionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ConversacionSerializer
    permission_classes = [IsAuthenticated, EsParticipanteDeConversacion]

    def get_queryset(self):
        queryset = Conversacion.objects.select_related(
            "denuncia__denunciante", "denuncia__profesional_asignado"
        )
        if self.action == "list":
            usuario = self.request.user
            # Only the reporter's or the currently assigned professional's.
            return queryset.filter(
                Q(denuncia__denunciante=usuario)
                | Q(denuncia__profesional_asignado=usuario)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        denuncia_id = request.data.get("denuncia")
        if not denuncia_id:
            raise ValidationError({"denuncia": "Este campo es obligatorio."})
        denuncia = (
            Denuncia.objects.select_related("denunciante", "profesional_asignado")
            .filter(pk=denuncia_id)
            .first()
        )
        if denuncia is None:
            raise ValidationError({"denuncia": "La denuncia no existe."})

        usuario = request.user
        if usuario.role == ROL_ADMIN:
            raise PermissionDenied(
                "El administrador no puede acceder a los chats privados."
            )
        es_duenio = denuncia.denunciante_id == usuario.id
        es_asignado = (
            usuario.role == ROL_PROFESIONAL
            and denuncia.profesional_asignado_id == usuario.id
        )
        # The owner always has access; a professional only when currently
        # assigned. The administrator and any other professional are denied.
        if not (es_duenio or es_asignado):
            raise PermissionDenied(
                "No tienes acceso a la conversación de esta denuncia."
            )

        conversacion, creada = Conversacion.objects.get_or_create(denuncia=denuncia)
        # Keep the legacy M2M coherent with the current authorization scope.
        participantes = [denuncia.denunciante]
        if denuncia.profesional_asignado_id:
            participantes.append(denuncia.profesional_asignado)
        conversacion.participantes.set(participantes)

        serializer = self.get_serializer(conversacion)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"])
    def mensajes(self, request, pk=None):
        conversacion = self.get_object()  # object permission -> 403 if not participant
        if request.method.lower() == "post":
            asegurar_editable(conversacion.denuncia)  # 409 if already finished
            contenido = (request.data.get("contenido") or "").strip()
            if not contenido:
                raise ValidationError({"contenido": "El mensaje no puede estar vacío."})
            mensaje = Mensaje.objects.create(
                conversacion=conversacion,
                remitente=request.user,
                contenido=contenido,
            )
            conversacion.save(update_fields=["actualizado_en"])
            broadcast_mensaje(mensaje)
            notificar_mensaje(mensaje)
            return Response(_serializar_mensaje(mensaje), status=status.HTTP_201_CREATED)

        mensajes = conversacion.mensajes.select_related("remitente").order_by("creado_en")
        page = self.paginate_queryset(mensajes)
        if page is not None:
            return self.get_paginated_response(MensajeSerializer(page, many=True).data)
        return Response(MensajeSerializer(mensajes, many=True).data)

    @action(detail=True, methods=["post"])
    def marcar_leidos(self, request, pk=None):
        conversacion = self.get_object()
        actualizados = (
            conversacion.mensajes.filter(leido=False)
            .exclude(remitente=request.user)
            .update(leido=True)
        )
        return Response({"actualizados": actualizados})
