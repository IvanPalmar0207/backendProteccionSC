"""Forum routes (mounted at /api/foro/)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PublicacionViewSet, RespuestaViewSet

router = DefaultRouter()
router.register("publicaciones", PublicacionViewSet, basename="publicacion")
router.register("respuestas", RespuestaViewSet, basename="respuesta")

urlpatterns = [path("", include(router.urls))]
