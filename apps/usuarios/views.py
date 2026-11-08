"""Registration, authentication and administrator user-management views."""

from django.contrib.auth import get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.permissions import IsAdministrador

from .serializers import (
    AdminUsuarioSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UsuarioSerializer,
)

Usuario = get_user_model()


class RegisterView(APIView):
    """Create a new USUARIO account (public endpoint)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "detail": "Cuenta creada correctamente. Ya puedes iniciar sesión.",
                "user": UsuarioSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """Obtain an access/refresh token pair and the authenticated profile."""

    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    """Return the authenticated account (identity and role)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


class AdminUsuarioViewSet(viewsets.ModelViewSet):
    """Administrator-only account management (role assignment included).

    Only this view can change ``role`` or ``is_active``. Users and
    professionals have no path to elevate their own privileges.
    """

    queryset = Usuario.objects.all().order_by("id")
    serializer_class = AdminUsuarioSerializer
    permission_classes = [IsAdministrador]
    http_method_names = ["get", "patch", "put", "head", "options"]
    search_fields = ["email", "nombre_completo"]

    def get_queryset(self):
        queryset = Usuario.objects.all().order_by("id")
        # The authenticated administrator is never part of the management list,
        # so the UI cannot offer to deactivate their own account.
        if self.action == "list":
            queryset = queryset.exclude(pk=self.request.user.pk)
        return queryset

    @staticmethod
    def _a_booleano(valor) -> bool:
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, int):
            return bool(valor)
        return str(valor).strip().lower() in ("true", "1", "yes", "si", "sí")

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Identity is checked server-side: never trust the id sent by Angular.
        if instance.pk == request.user.pk and request.data.get("is_active") is not None:
            solicitado = self._a_booleano(request.data.get("is_active"))
            if solicitado != instance.is_active:
                raise ValidationError(
                    {"is_active": "No puedes cambiar el estado de tu propia cuenta."}
                )
        return super().update(request, *args, **kwargs)
