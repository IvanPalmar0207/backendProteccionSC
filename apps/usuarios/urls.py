"""Authentication and user-administration routes (mounted at /api/auth/)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .recovery_views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetValidateView,
)
from .views import AdminUsuarioViewSet, LoginView, MeView, RegisterView

router = DefaultRouter()
router.register("usuarios", AdminUsuarioViewSet, basename="admin-usuario")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password-reset/validate/",
        PasswordResetValidateView.as_view(),
        name="password-reset-validate",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("", include(router.urls)),
]
