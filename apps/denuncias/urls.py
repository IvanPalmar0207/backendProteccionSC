"""Report routes (mounted at /api/denuncias/)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdminDenunciaViewSet, DenunciaViewSet, ProfesionalDenunciaViewSet

router = DefaultRouter()
router.register("mis-denuncias", DenunciaViewSet, basename="mis-denuncias")
router.register(
    "profesional", ProfesionalDenunciaViewSet, basename="profesional-denuncias"
)
router.register("admin", AdminDenunciaViewSet, basename="admin-denuncias")

urlpatterns = [
    path("", include(router.urls)),
]
