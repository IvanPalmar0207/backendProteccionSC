"""Chat routes (mounted at /api/chat/)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConversacionViewSet

router = DefaultRouter()
router.register("conversaciones", ConversacionViewSet, basename="conversacion")

urlpatterns = [
    path("", include(router.urls)),
]
