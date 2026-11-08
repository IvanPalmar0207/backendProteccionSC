"""Authentication and role tests (S7, S8, S20)."""

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from rest_framework.test import APITestCase

Usuario = get_user_model()


class RegistrationTests(APITestCase):
    def test_register_creates_usuario_role(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "nueva@test.dev",
                "nombre_completo": "Nueva Persona",
                "documento": documento_unico(),
                "password": "Usuario123*",
                "password_confirm": "Usuario123*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["role"], "USUARIO")
        self.assertTrue(Usuario.objects.filter(email="nueva@test.dev").exists())

    def test_duplicate_email_is_rejected(self):
        Usuario.objects.create_user(documento=documento_unico(), email="dup@test.dev", password="Usuario123*", nombre_completo="Dup")
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "dup@test.dev",
                "nombre_completo": "Dup",
                "documento": documento_unico(),
                "password": "Usuario123*",
                "password_confirm": "Usuario123*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "no-es-un-email",
                "nombre_completo": "X",
                "documento": documento_unico(),
                "password": "Usuario123*",
                "password_confirm": "Usuario123*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_required_fields_are_validated(self):
        response = self.client.post("/api/auth/register/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        for field in ("email", "nombre_completo", "documento", "password"):
            self.assertIn(field, response.data)

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "mismatch@test.dev",
                "nombre_completo": "X",
                "documento": documento_unico(),
                "password": "Usuario123*",
                "password_confirm": "Otro123*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirm", response.data)

    def test_registration_cannot_set_admin_role(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "sneaky@test.dev",
                "nombre_completo": "Sneaky",
                "documento": documento_unico(),
                "password": "Usuario123*",
                "password_confirm": "Usuario123*",
                "role": "ADMINISTRADOR",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Usuario.objects.get(email="sneaky@test.dev").role, "USUARIO")


class LoginTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(documento=documento_unico(), 
            email="login@test.dev", password="Usuario123*", nombre_completo="Login", role="USUARIO"
        )

    def test_valid_credentials_return_tokens_and_role(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "login@test.dev", "password": "Usuario123*"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], "USUARIO")

    def test_invalid_credentials_are_rejected(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "login@test.dev", "password": "incorrecta"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.data)

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        self.client.force_authenticate(user=self.usuario)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "login@test.dev")
