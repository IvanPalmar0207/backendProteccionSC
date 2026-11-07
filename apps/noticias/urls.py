"""News routes (mounted at /api/noticias/)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NoticiaViewSet

router = DefaultRouter()
router.register("", NoticiaViewSet, basename="noticia")

urlpatterns = [path("", include(router.urls))]
