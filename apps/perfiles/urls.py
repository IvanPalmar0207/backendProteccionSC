"""Profile routes (mounted at /api/perfiles/)."""

from django.urls import path

from .views import MiPerfilView

urlpatterns = [
    path("mi-perfil/", MiPerfilView.as_view(), name="mi-perfil"),
]
