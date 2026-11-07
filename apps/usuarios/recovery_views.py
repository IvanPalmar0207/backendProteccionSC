"""Password recovery endpoints.

The frontend never decides whether a token is valid: it asks the backend
(``PasswordResetValidateView``) and the backend applies every rule.
"""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.throttling import PasswordResetThrottle

from .serializers import PasswordResetConfirmSerializer, PasswordResetRequestSerializer
from .services import (
    buscar_token,
    consumir_token,
    crear_token_recuperacion,
    enviar_correo_recuperacion,
    token_es_valido,
)

logger = logging.getLogger(__name__)

Usuario = get_user_model()

MENSAJE_GENERICO = (
    "Si el correo está registrado, te enviamos un enlace para restablecer tu "
    "contraseña. Revisá tu bandeja de entrada."
)
MENSAJE_TOKEN_INVALIDO = "El enlace es inválido o expiró. Solicitá uno nuevo."


class PasswordResetRequestView(APIView):
    """Request a single-use recovery link. Always generic for unknown emails."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()

        usuario = Usuario.objects.filter(email=email, is_active=True).first()
        if usuario is not None:
            raw_token = crear_token_recuperacion(usuario)
            try:
                enviar_correo_recuperacion(usuario, raw_token)
            except Exception:  # noqa: BLE001 - never simulate a successful send
                logger.exception("No se pudo enviar el correo de recuperación.")
                return Response(
                    {
                        "detail": (
                            "No pudimos enviar el correo en este momento. "
                            "Intentá nuevamente más tarde."
                        )
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        return Response({"detail": MENSAJE_GENERICO}, status=status.HTTP_200_OK)


class PasswordResetValidateView(APIView):
    """Tell the SPA whether a token can still be used, without extra detail."""

    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token", "")
        return Response({"valido": token_es_valido(token)})


class PasswordResetConfirmView(APIView):
    """Set a new password, burn the token and revoke refresh tokens."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registro = buscar_token(serializer.validated_data["token"])
        if registro is None or not registro.vigente:
            return Response(
                {"detail": MENSAJE_TOKEN_INVALIDO}, status=status.HTTP_400_BAD_REQUEST
            )

        # Re-validate with the account context (similarity to email/name), the
        # same rule used by registration.
        try:
            validate_password(serializer.validated_data["password"], user=registro.usuario)
        except DjangoValidationError as error:
            return Response(
                {"password": list(error.messages)}, status=status.HTTP_400_BAD_REQUEST
            )

        consumir_token(registro, serializer.validated_data["password"])
        return Response(
            {"detail": "Contraseña actualizada correctamente. Ya podés iniciar sesión."},
            status=status.HTTP_200_OK,
        )
