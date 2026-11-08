"""Document integrity: mandatory, unique, string-preserving and immutable (Fase 10)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from apps.core.tests.factories import documento_unico

Usuario = get_user_model()

PERFIL = "/api/perfiles/mi-perfil/"


class DocumentoModeloTests(APITestCase):
    def test_documento_es_obligatorio(self):
        candidato = Usuario(email="sin-doc@test.dev", nombre_completo="Sin Doc", role="USUARIO")
        with self.assertRaises(ValidationError) as contexto:
            candidato.full_clean(exclude=["password"])
        self.assertIn("documento", contexto.exception.message_dict)

    def test_documento_es_unico_en_la_base_de_datos(self):
        Usuario.objects.create_user(
            email="a@test.dev", password="Usuario123*", nombre_completo="A", documento="UNICO-1"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Usuario.objects.create_user(
                    email="b@test.dev",
                    password="Usuario123*",
                    nombre_completo="B",
                    documento="UNICO-1",
                )
        self.assertEqual(Usuario.objects.filter(documento="UNICO-1").count(), 1)

    def test_ceros_iniciales_se_conservan_como_cadena(self):
        usuario = Usuario.objects.create_user(
            email="ceros@test.dev",
            password="Usuario123*",
            nombre_completo="Ceros",
            documento="000123",
        )
        usuario.refresh_from_db()
        self.assertEqual(usuario.documento, "000123")
        self.assertIsInstance(usuario.documento, str)


class DocumentoRegistroTests(APITestCase):
    def _payload(self, documento: str, email: str = "registro@test.dev") -> dict:
        return {
            "email": email,
            "nombre_completo": "Persona Registro",
            "documento": documento,
            "password": "Usuario123*",
            "password_confirm": "Usuario123*",
        }

    def test_registro_sin_documento_es_rechazado(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "sindoc@test.dev",
                "nombre_completo": "Sin Doc",
                "password": "Usuario123*",
                "password_confirm": "Usuario123*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("documento", response.data)

    def test_registro_con_documento_vacio_o_solo_espacios_es_rechazado(self):
        for indice, documento in enumerate(["", "   "]):
            response = self.client.post(
                "/api/auth/register/",
                self._payload(documento, email=f"vacio{indice}@test.dev"),
                format="json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("documento", response.data)

    def test_registro_con_documento_duplicado_es_rechazado(self):
        Usuario.objects.create_user(
            email="existente@test.dev",
            password="Usuario123*",
            nombre_completo="Existente",
            documento="DOC-DUP",
        )
        response = self.client.post(
            "/api/auth/register/", self._payload("DOC-DUP", email="nuevo@test.dev"), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("documento", response.data)
        # The error never leaks another account's email.
        self.assertNotIn("existente@test.dev", str(response.data))

    def test_registro_con_correo_y_documento_duplicados_rechaza_ambos(self):
        Usuario.objects.create_user(
            email="dup-ambos@test.dev",
            password="Usuario123*",
            nombre_completo="Dup Ambos",
            documento="DOC-AMBOS",
        )
        response = self.client.post(
            "/api/auth/register/",
            self._payload("DOC-AMBOS", email="dup-ambos@test.dev"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.assertIn("documento", response.data)

    def test_conflicto_de_correo_por_concurrencia_devuelve_400_estructurado(self):
        from unittest.mock import patch

        with patch(
            "apps.usuarios.serializers.Usuario.objects.create_user",
            side_effect=IntegrityError("UNIQUE constraint failed: usuarios_usuario.email"),
        ):
            response = self.client.post(
                "/api/auth/register/",
                self._payload("DOC-RACE-EMAIL", email="race-email@test.dev"),
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_conflicto_de_documento_por_concurrencia_devuelve_400_estructurado(self):
        from unittest.mock import patch

        with patch(
            "apps.usuarios.serializers.Usuario.objects.create_user",
            side_effect=IntegrityError("UNIQUE constraint failed: usuarios_usuario.documento"),
        ):
            response = self.client.post(
                "/api/auth/register/",
                self._payload("DOC-RACE-DOC", email="race-doc@test.dev"),
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("documento", response.data)

    def test_registro_conserva_ceros_iniciales(self):
        response = self.client.post(
            "/api/auth/register/", self._payload("000777", email="ceros-reg@test.dev"), format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Usuario.objects.get(email="ceros-reg@test.dev").documento, "000777")


class DocumentoInmutableRolesTests(APITestCase):
    def test_los_tres_roles_no_pueden_cambiar_su_documento(self):
        admin = Usuario.objects.create_superuser(
            email="doc-admin@test.dev",
            password="Admin123*",
            nombre_completo="Admin Doc",
            documento=documento_unico(),
        )
        profesional = Usuario.objects.create_user(
            email="doc-prof@test.dev",
            password="Prof123*",
            nombre_completo="Prof Doc",
            documento=documento_unico(),
            role="PROFESIONAL",
        )
        usuario = Usuario.objects.create_user(
            email="doc-user@test.dev",
            password="Usuario123*",
            nombre_completo="User Doc",
            documento=documento_unico(),
            role="USUARIO",
        )
        for persona in (admin, profesional, usuario):
            original = persona.documento
            self.client.force_authenticate(user=persona)
            response = self.client.patch(
                PERFIL, {"documento": "CAMBIO-1"}, format="json"
            )
            self.assertEqual(response.status_code, 400)
            persona.refresh_from_db()
            self.assertEqual(persona.documento, original)


class DocumentoCreacionSinBypassTests(APITestCase):
    """No production path may create an account with an empty/duplicate document."""

    def test_manager_create_user_sin_documento_no_crea_cuenta(self):
        with self.assertRaises((ValidationError, ValueError, IntegrityError)):
            Usuario.objects.create_user(
                email="manager-sin-doc@test.dev",
                password="Usuario123*",
                nombre_completo="Sin Doc Manager",
            )
        self.assertFalse(Usuario.objects.filter(email="manager-sin-doc@test.dev").exists())

    def test_manager_create_superuser_sin_documento_no_crea_cuenta(self):
        with self.assertRaises((ValidationError, ValueError, IntegrityError)):
            Usuario.objects.create_superuser(
                email="root-sin-doc@test.dev",
                password="Admin123*",
                nombre_completo="Root Sin Doc",
            )
        self.assertFalse(Usuario.objects.filter(email="root-sin-doc@test.dev").exists())

    def test_admin_add_rechaza_cuenta_sin_documento(self):
        root = Usuario.objects.create_superuser(
            email="root-doc@test.dev",
            password="Admin123*",
            nombre_completo="Root",
            documento=documento_unico(),
        )
        self.client.force_login(root)
        response = self.client.post(
            "/admin/usuarios/usuario/add/",
            {
                "email": "admin-sin-doc@test.dev",
                "nombre_completo": "Sin Doc Admin",
                "role": "USUARIO",
                "password1": "Usuario123*",
                "password2": "Usuario123*",
            },
        )
        # The form re-renders with an error instead of creating the account.
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Usuario.objects.filter(email="admin-sin-doc@test.dev").exists())

    def test_registro_rechaza_variante_case_de_documento_existente(self):
        Usuario.objects.create_user(
            email="case-base@test.dev",
            password="Usuario123*",
            nombre_completo="Base",
            documento="ABC-1",
        )
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "case-nuevo@test.dev",
                "nombre_completo": "Nuevo",
                "documento": "abc-1",
                "password": "Usuario123*",
                "password_confirm": "Usuario123*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("documento", response.data)
