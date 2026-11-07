"""Report endpoints.

Two separate viewsets keep the role split explicit:

* ``DenunciaViewSet`` — the owner's own reports (role USUARIO).
* ``ProfesionalDenunciaViewSet`` — the attention module (role PROFESIONAL),
  which uses the anonymity-safe serializer.

A user can never reach another account's reports because the queryset is
filtered by ``request.user``. A professional can only see what the
professional serializer renders, where anonymous reporters are ``None``.
"""

from django.contrib.auth import get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.core.permissions import IsProfesional, IsUsuario
from apps.notificaciones.models import TipoNotificacionChoices
from apps.notificaciones.services import notificar

from .models import Denuncia, EstadoChoices, SeguimientoDenuncia
from .serializers import (
    DenunciaCreateSerializer,
    DenunciaEstadoUpdateSerializer,
    DenunciaProfesionalSerializer,
    DenunciaUsuarioSerializer,
)

Usuario = get_user_model()


class DenunciaViewSet(viewsets.ModelViewSet):
    """Owner-facing CRUD. Reports are always created for ``request.user``."""

    permission_classes = [IsUsuario]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        # Hard isolation: only the authenticated user's own reports.
        return (
            Denuncia.objects.filter(denunciante=self.request.user)
            .select_related("denunciante", "profesional_asignado")
            .prefetch_related("seguimientos")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return DenunciaCreateSerializer
        return DenunciaUsuarioSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        denuncia = serializer.save(denunciante=request.user)
        SeguimientoDenuncia.objects.create(
            denuncia=denuncia,
            autor=request.user,
            estado_nuevo=denuncia.estado,
            observacion="Denuncia registrada.",
        )
        notificar(
            request.user,
            "Denuncia registrada",
            f"Tu denuncia {denuncia.identificador} fue registrada correctamente.",
            tipo=TipoNotificacionChoices.DENUNCIA,
            url=f"/usuario/denuncias/{denuncia.id}",
        )
        return Response(
            {
                "detail": "Denuncia registrada correctamente.",
                "denuncia": DenunciaUsuarioSerializer(denuncia).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfesionalDenunciaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Attention module for professionals. Uses the anonymity-safe serializer."""

    permission_classes = [IsProfesional]
    serializer_class = DenunciaProfesionalSerializer

    def get_queryset(self):
        queryset = (
            Denuncia.objects.all()
            .select_related("denunciante", "profesional_asignado")
            .prefetch_related("seguimientos")
        )
        estado = self.request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        modalidad = self.request.query_params.get("modalidad")
        if modalidad:
            queryset = queryset.filter(modalidad=modalidad)
        solo_mias = self.request.query_params.get("mis_denuncias")
        if solo_mias == "true":
            queryset = queryset.filter(profesional_asignado=self.request.user)
        return queryset

    @action(detail=True, methods=["post"])
    def asignarme(self, request, pk=None):
        denuncia = self.get_object()
        denuncia.profesional_asignado = request.user
        if denuncia.estado == EstadoChoices.PENDIENTE:
            estado_anterior = denuncia.estado
            denuncia.estado = EstadoChoices.EN_PROCESO
        else:
            estado_anterior = denuncia.estado
        denuncia.save(update_fields=["profesional_asignado", "estado", "actualizado_en"])
        SeguimientoDenuncia.objects.create(
            denuncia=denuncia,
            autor=request.user,
            estado_anterior=estado_anterior,
            estado_nuevo=denuncia.estado,
            observacion="Caso asignado a un profesional.",
        )
        return Response(self.get_serializer(denuncia).data)

    @action(detail=True, methods=["post"])
    def cambiar_estado(self, request, pk=None):
        denuncia = self.get_object()
        if denuncia.profesional_asignado_id not in (None, request.user.id):
            raise PermissionDenied("Este caso está asignado a otro profesional.")
        serializer = DenunciaEstadoUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estado_anterior = denuncia.estado
        denuncia.estado = serializer.validated_data["estado"]
        if denuncia.profesional_asignado_id is None:
            denuncia.profesional_asignado = request.user
        denuncia.save(update_fields=["estado", "profesional_asignado", "actualizado_en"])
        SeguimientoDenuncia.objects.create(
            denuncia=denuncia,
            autor=request.user,
            estado_anterior=estado_anterior,
            estado_nuevo=denuncia.estado,
            observacion=serializer.validated_data.get("observacion", ""),
        )
        notificar(
            denuncia.denunciante,
            "Tu denuncia fue actualizada",
            f"El estado de la denuncia {denuncia.identificador} ahora es "
            f"{denuncia.get_estado_display()}.",
            tipo=TipoNotificacionChoices.ESTADO,
            url=f"/usuario/denuncias/{denuncia.id}",
        )
        return Response(self.get_serializer(denuncia).data)
