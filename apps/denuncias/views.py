"""Report endpoints.

* ``DenunciaViewSet`` — the owner's own reports (role USUARIO). Creating one
  auto-assigns the least-loaded active professional.
* ``ProfesionalDenunciaViewSet`` — the attention module (role PROFESIONAL). A
  professional only ever reaches reports assigned to them.
* ``AdminDenunciaViewSet`` — administrative supervision and manual assignment
  (anonymity-safe serializer; chat content is never exposed here).

Identity is never leaked: the professional serializer renders ``solicitante``
as ``None`` for anonymous reports, and the admin endpoint uses it too.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.permissions import IsAdministrador, IsProfesional, IsUsuario
from apps.notificaciones.models import TipoNotificacionChoices
from apps.notificaciones.services import notificar

from .models import Denuncia, EstadoChoices, SeguimientoDenuncia
from .serializers import (
    DenunciaCreateSerializer,
    DenunciaEstadoUpdateSerializer,
    DenunciaProfesionalSerializer,
    DenunciaUsuarioSerializer,
)
from .services import (
    asegurar_editable,
    asignar_profesional_automatico,
    profesionales_habilitados,
    refrescar_seguimientos,
    registrar_pendiente_de_asignacion,
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
        with transaction.atomic():
            denuncia = serializer.save(denunciante=request.user)
            SeguimientoDenuncia.objects.create(
                denuncia=denuncia,
                autor=request.user,
                estado_nuevo=denuncia.estado,
                observacion="Denuncia registrada.",
            )
            # Balanced automatic assignment; never from the client.
            profesional = asignar_profesional_automatico(denuncia)
            if profesional is None:
                registrar_pendiente_de_asignacion(denuncia)
        denuncia.refresh_from_db()
        notificar(
            request.user,
            "Denuncia registrada",
            f"Tu denuncia {denuncia.identificador} fue registrada correctamente.",
            tipo=TipoNotificacionChoices.DENUNCIA,
            url=f"/usuario/denuncias/{denuncia.id}",
        )
        if profesional is not None:
            notificar(
                profesional,
                "Nuevo caso asignado",
                f"Se te asignó la denuncia {denuncia.identificador}.",
                tipo=TipoNotificacionChoices.DENUNCIA,
                url=f"/profesional/denuncias/{denuncia.id}",
            )
        return Response(
            {
                "detail": "Denuncia registrada correctamente.",
                "denuncia": DenunciaUsuarioSerializer(
                    denuncia, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfesionalDenunciaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Attention module: only the caller's assigned cases, always."""

    permission_classes = [IsProfesional]
    serializer_class = DenunciaProfesionalSerializer

    def get_queryset(self):
        # Strict isolation: only reports currently assigned to the caller.
        # Unassigned reports and other professionals' cases are invisible,
        # including by direct id.
        queryset = (
            Denuncia.objects.filter(profesional_asignado=self.request.user)
            .select_related("denunciante", "profesional_asignado")
            .prefetch_related("seguimientos")
        )
        estado = self.request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        modalidad = self.request.query_params.get("modalidad")
        if modalidad:
            queryset = queryset.filter(modalidad=modalidad)
        return queryset

    @action(detail=True, methods=["post"])
    def cambiar_estado(self, request, pk=None):
        denuncia = self.get_object()  # 404 unless assigned to the caller
        asegurar_editable(denuncia)  # 409 if already finished
        serializer = DenunciaEstadoUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estado_anterior = denuncia.estado
        denuncia.estado = serializer.validated_data["estado"]
        denuncia.save(update_fields=["estado", "actualizado_en"])
        SeguimientoDenuncia.objects.create(
            denuncia=denuncia,
            autor=request.user,
            estado_anterior=estado_anterior,
            estado_nuevo=denuncia.estado,
            observacion=serializer.validated_data.get("observacion", ""),
        )
        refrescar_seguimientos(denuncia)
        notificar(
            denuncia.denunciante,
            "Tu denuncia fue actualizada",
            f"El estado de la denuncia {denuncia.identificador} ahora es "
            f"{denuncia.get_estado_display()}.",
            tipo=TipoNotificacionChoices.ESTADO,
            url=f"/usuario/denuncias/{denuncia.id}",
        )
        return Response(self.get_serializer(denuncia).data)


class AdminDenunciaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Administrative supervision and manual (re)assignment.

    Uses the anonymity-safe serializer, so an anonymous reporter's identity is
    never exposed. Administrators still cannot read private chats.
    """

    permission_classes = [IsAdministrador]
    serializer_class = DenunciaProfesionalSerializer

    def get_queryset(self):
        queryset = (
            Denuncia.objects.select_related("denunciante", "profesional_asignado")
            .prefetch_related("seguimientos")
        )
        estado = self.request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        asignacion = self.request.query_params.get("asignacion")
        if asignacion == "pendientes":
            queryset = queryset.filter(profesional_asignado__isnull=True)
        elif asignacion == "asignadas":
            queryset = queryset.filter(profesional_asignado__isnull=False)
        return queryset

    @action(detail=False, methods=["get"])
    def profesionales(self, request):
        """Active professionals available for manual assignment."""
        return Response(
            [
                {
                    "id": profesional.id,
                    "nombre_completo": profesional.nombre_completo,
                    "casos_activos": profesional.casos_activos,
                }
                for profesional in profesionales_habilitados()
            ]
        )

    @action(detail=True, methods=["post"])
    def asignar(self, request, pk=None):
        denuncia = self.get_object()
        asegurar_editable(denuncia)  # 409 if already finished
        profesional_id = request.data.get("profesional")
        if profesional_id in (None, ""):
            raise ValidationError({"profesional": "Este campo es obligatorio."})
        profesional = Usuario.objects.filter(
            pk=profesional_id, role="PROFESIONAL", is_active=True
        ).first()
        if profesional is None:
            raise ValidationError(
                {"profesional": "El profesional no existe o no está habilitado."}
            )

        with transaction.atomic():
            anterior = denuncia.profesional_asignado
            estado_anterior = denuncia.estado
            denuncia.profesional_asignado = profesional
            if denuncia.estado == EstadoChoices.PENDIENTE:
                denuncia.estado = EstadoChoices.EN_PROCESO
            denuncia.save(
                update_fields=["profesional_asignado", "estado", "actualizado_en"]
            )
            if anterior is None:
                observacion = (
                    f"Caso asignado por administración a {profesional.nombre_completo}."
                )
            elif anterior.pk != profesional.pk:
                observacion = (
                    f"Reasignado de {anterior.nombre_completo} "
                    f"a {profesional.nombre_completo}."
                )
            else:
                observacion = "Asignación confirmada por administración."
            SeguimientoDenuncia.objects.create(
                denuncia=denuncia,
                autor=request.user,
                estado_anterior=estado_anterior,
                estado_nuevo=denuncia.estado,
                observacion=observacion,
            )
            refrescar_seguimientos(denuncia)
        denuncia.refresh_from_db()
        notificar(
            profesional,
            "Caso asignado",
            f"Se te asignó la denuncia {denuncia.identificador}.",
            tipo=TipoNotificacionChoices.DENUNCIA,
            url=f"/profesional/denuncias/{denuncia.id}",
        )
        return Response(self.get_serializer(denuncia).data)
