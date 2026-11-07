"""Password recovery tests (F2-S12, F2-S16)."""

import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.usuarios.models import TokenRecuperacion
from apps.usuarios.services import crear_token_recuperacion

Usuario = get_user_model()

REQUEST_URL = "/api/auth/password-reset/"
VALIDATE_URL = "/api/auth/password-reset/validate/"
CONFIRM_URL = "/api/auth/password-reset/confirm/"


def extraer_token(body: str) -> str:
    return re.search(r"token=([A-Za-z0-9_\-]+)", body).group(1)


class PasswordResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.usuario = Usuario.objects.create_user(
            email="recuperacion@test.dev",
            password="Usuario123*",
            nombre_completo="Recuperación Prueba",
        )

    def _solicitar(self, email: str):
        return self.client.post(REQUEST_URL, {"email": email}, format="json")

    def _confirmar(self, token: str, password: str, confirmacion: str | None = None):
        return self.client.post(
            CONFIRM_URL,
            {"token": token, "password": password, "password_confirm": confirmacion or password},
            format="json",
        )

    # -- request -----------------------------------------------------------
    def test_unknown_email_returns_generic_answer(self):
        respuesta = self._solicitar("noexiste@test.dev")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_known_email_sends_link_and_stores_only_hash(self):
        token = "secreto-en-claro"
        respuesta = self._solicitar("recuperacion@test.dev")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        raw = extraer_token(mail.outbox[0].body)
        self.assertNotEqual(raw, token)
        self.assertFalse(TokenRecuperacion.objects.filter(token_hash=raw).exists())
        self.assertTrue(TokenRecuperacion.objects.filter(usuario=self.usuario, usado=False).exists())

    def test_invalid_email_format_is_rejected(self):
        respuesta = self._solicitar("no-es-email")
        self.assertEqual(respuesta.status_code, 400)

    def test_requesting_again_invalidates_previous_token(self):
        self._solicitar("recuperacion@test.dev")
        primer_token = extraer_token(mail.outbox[0].body)
        self._solicitar("recuperacion@test.dev")
        segundo_token = extraer_token(mail.outbox[1].body)

        self.assertEqual(self._confirmar(primer_token, "NuevaPass123*").status_code, 400)
        self.assertEqual(self._confirmar(segundo_token, "NuevaPass123*").status_code, 200)

    # -- validate ----------------------------------------------------------
    def test_validate_endpoint_is_authoritative(self):
        self._solicitar("recuperacion@test.dev")
        token = extraer_token(mail.outbox[0].body)
        self.assertTrue(self.client.get(f"{VALIDATE_URL}?token={token}").data["valido"])
        self.assertFalse(self.client.get(f"{VALIDATE_URL}?token=inventado").data["valido"])

    # -- confirm -----------------------------------------------------------
    def test_confirm_changes_password_and_token_becomes_single_use(self):
        self._solicitar("recuperacion@test.dev")
        token = extraer_token(mail.outbox[0].body)

        respuesta = self._confirmar(token, "NuevaClave123*")
        self.assertEqual(respuesta.status_code, 200)

        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("NuevaClave123*"))

        # Reusing the same link must fail.
        self.assertEqual(self._confirmar(token, "OtraClave123*").status_code, 400)

        # The normal authentication flow accepts the new password.
        login = self.client.post(
            "/api/auth/login/",
            {"email": "recuperacion@test.dev", "password": "NuevaClave123*"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)

    def test_expired_token_is_rejected(self):
        token = crear_token_recuperacion(self.usuario)
        TokenRecuperacion.objects.filter(usuario=self.usuario).update(
            expira_en=timezone.now() - timedelta(minutes=1)
        )
        self.assertEqual(self._confirmar(token, "NuevaClave123*").status_code, 400)

    def test_invalid_token_is_rejected(self):
        self.assertEqual(self._confirmar("token-inventado", "NuevaClave123*").status_code, 400)

    def test_weak_password_is_rejected(self):
        self._solicitar("recuperacion@test.dev")
        token = extraer_token(mail.outbox[0].body)
        respuesta = self._confirmar(token, "123")
        self.assertEqual(respuesta.status_code, 400)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("Usuario123*"))

    def test_password_mismatch_is_rejected(self):
        self._solicitar("recuperacion@test.dev")
        token = extraer_token(mail.outbox[0].body)
        self.assertEqual(
            self._confirmar(token, "NuevaClave123*", "OtraClave123*").status_code, 400
        )

    def test_refresh_tokens_are_revoked_after_reset(self):
        login = self.client.post(
            "/api/auth/login/",
            {"email": "recuperacion@test.dev", "password": "Usuario123*"},
            format="json",
        )
        refresh_token = login.data["refresh"]

        self._solicitar("recuperacion@test.dev")
        token = extraer_token(mail.outbox[0].body)
        self.assertEqual(self._confirmar(token, "NuevaClave123*").status_code, 200)

        # The refresh token issued before the reset is now blacklisted.
        regenerado = self.client.post(
            "/api/auth/refresh/", {"refresh": refresh_token}, format="json"
        )
        self.assertEqual(regenerado.status_code, 401)

    @override_settings(PASSWORD_RESET_RATE="2/hour")
    def test_rate_limit_blocks_abuse(self):
        self._solicitar("recuperacion@test.dev")
        self._solicitar("recuperacion@test.dev")
        respuesta = self._solicitar("recuperacion@test.dev")
        self.assertEqual(respuesta.status_code, 429)
