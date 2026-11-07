"""Podcast endpoints: published content is public, management is admin-only."""

from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Podcast
from .serializers import PodcastSerializer


class PodcastViewSet(viewsets.ModelViewSet):
    serializer_class = PodcastSerializer
    queryset = Podcast.objects.all()

    def get_permissions(self):
        from apps.core.permissions import IsAdministrador

        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdministrador()]

    def get_queryset(self):
        queryset = Podcast.objects.select_related("autor")
        user = self.request.user
        es_admin = user.is_authenticated and user.role == "ADMINISTRADOR"
        if self.action in ("list", "retrieve") and not es_admin:
            queryset = queryset.filter(publicado=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)
