"""News endpoints: published content is public, management is admin-only."""

from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from apps.core.permissions import IsAdministrador

from .models import Noticia
from .serializers import NoticiaSerializer


class NoticiaViewSet(viewsets.ModelViewSet):
    serializer_class = NoticiaSerializer
    queryset = Noticia.objects.all()

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdministrador()]

    def get_queryset(self):
        queryset = Noticia.objects.select_related("autor")
        user = self.request.user
        es_admin = user.is_authenticated and user.role == "ADMINISTRADOR"
        if self.action in ("list", "retrieve") and not es_admin:
            queryset = queryset.filter(publicado=True)

        categoria = self.request.query_params.get("categoria")
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        destacada = self.request.query_params.get("destacada")
        if destacada is not None and destacada != "":
            queryset = queryset.filter(destacada=destacada.lower() in ("1", "true", "yes"))
        return queryset

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)
