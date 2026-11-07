"""Chat REST endpoints.

List is filtered to the caller's conversations; detail and actions rely on the
object-level ``EsParticipanteDeConversacion`` permission, so a non-participant
(including an administrator) receives 403.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.denuncias.models import Denuncia

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
        queryset = Conversacion.objects.select_related("denuncia").prefetch_related(
            "participantes"
        )
        if self.action == "list":
            # Only the caller's conversations are even visible.
            return queryset.filter(participantes=self.request.user)
        return queryset

    def create(self, request, *args, **kwargs):
        denuncia_id = request.data.get("denuncia")
        if not denuncia_id:
            raise ValidationError({"denuncia": "Este campo es obligatorio."})
        try:
            denuncia = Denuncia.objects.get(pk=denuncia_id)
        except (Denuncia.DoesNotExist, ValueError):
            raise ValidationError({"denuncia": "La denuncia no existe."})

        usuario = request.user
        if usuario.role == ROL_ADMIN:
            raise PermissionDenied("El administrador no puede acceder a los chats privados.")

        es_duenio = denuncia.denunciante_id == usuario.id
        es_profesional = usuario.role == ROL_PROFESIONAL
        if not (es_duenio or es_profesional):
            raise PermissionDenied("No podés iniciar una conversación sobre esta denuncia.")

        conversacion, creada = Conversacion.objects.get_or_create(denuncia=denuncia)
        conversacion.participantes.add(denuncia.denunciante)
        if es_profesional:
            conversacion.participantes.add(usuario)
            if denuncia.profesional_asignado_id is None:
                denuncia.profesional_asignado = usuario
                denuncia.save(update_fields=["profesional_asignado", "actualizado_en"])
        elif denuncia.profesional_asignado_id:
            conversacion.participantes.add(denuncia.profesional_asignado)

        if not es_profesional and conversacion.participantes.count() < 2:
            # The owner may open the thread before a professional is assigned;
            # that is allowed and the professional joins later.
            pass

        serializer = self.get_serializer(conversacion)
        return Response(serializer.data, status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"])
    def mensajes(self, request, pk=None):
        conversacion = self.get_object()  # object permission -> 403 if not participant
        if request.method.lower() == "post":
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
