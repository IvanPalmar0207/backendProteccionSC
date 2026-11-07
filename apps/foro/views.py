"""Forum endpoints.

Authenticated users read and participate; authors (and administrators) may
edit or delete their own content. Administrators can manage every publication
and reply (HU-08.5).
"""

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from .models import Publicacion, Respuesta
from .serializers import PublicacionSerializer, RespuestaSerializer


class EsAutorOAdministrador(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        if getattr(request.user, "role", None) == "ADMINISTRADOR":
            return True
        return obj.autor_id == request.user.id


class PublicacionViewSet(viewsets.ModelViewSet):
    queryset = Publicacion.objects.select_related("autor").prefetch_related("respuestas__autor")
    serializer_class = PublicacionSerializer
    permission_classes = [IsAuthenticated, EsAutorOAdministrador]
    search_fields = ["titulo", "contenido"]

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)

    @action(detail=True, methods=["post"])
    def responder(self, request, pk=None):
        publicacion = self.get_object()
        contenido = (request.data.get("contenido") or "").strip()
        if not contenido:
            raise PermissionDenied("La respuesta no puede estar vacía.")
        respuesta = Respuesta.objects.create(
            publicacion=publicacion, autor=request.user, contenido=contenido
        )
        return Response(
            RespuestaSerializer(respuesta).data, status=status.HTTP_201_CREATED
        )


class RespuestaViewSet(
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Deletion of a reply by its author or an administrator."""

    queryset = Respuesta.objects.select_related("autor")
    serializer_class = RespuestaSerializer
    permission_classes = [IsAuthenticated, EsAutorOAdministrador]
    http_method_names = ["delete", "head", "options"]
