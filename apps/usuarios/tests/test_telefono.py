"""Phone validation on registration, profile and admin endpoints (Fase 11)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.tests.factories import documento_unico

Usuario = get_user_model()
PERFIL = "/api/perfiles/mi-perfil/"

INVALIDOS = [
    "300ABC4567",
    "300-123-4567",
    "300 123 4567",
    "+573001234567",
    "300.123.4567",
    "300/123/4567",
]


class TelefonoRegistroTests(APITestCase):
    def _payload(self, telefono: str, email: str) -> dict:
        return {
            "email": email,
            "nombre_completo": "Telefono Registro",
            "documento": documento_unico(),
            "telefono": telefono,
            "password": "Usuario123*",
            "password_confirm": "Usuario123*",
        }

    def test_telefono_valido_es_aceptado(self):
        response = self.client.post(
            "/api/auth/register/",
            self._payload("3001234567", "tel-ok@test.dev"),
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_telefono_omitido_es_aceptado(self):
        payload = self._payload("3001234567", "tel-omitido@test.dev")
        del payload["telefono"]
        self.assertEqual(
            self.client.post("/api/auth/register/", payload, format="json").status_code, 201
        )

    def test_telefonos_invalidos_son_rechazados(self):
        for indice, telefono in enumerate(INVALIDOS):
            response = self.client.post(
                "/api/auth/register/",
                self._payload(telefono, f"tel-inv-{indice}@test.dev"),
                format="json",
            )
            self.assertEqual(response.status_code, 400, telefono)
            self.assertIn("telefono", response.data, telefono)


class TelefonoPerfilTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email="tel-perfil@test.dev",
            password="Usuario123*",
            nombre_completo="Tel Perfil",
            telefono="3001234567",
            documento=documento_unico(),
        )
        self.client.force_authenticate(user=self.usuario)

    def test_perfil_acepta_telefono_valido(self):
        response = self.client.patch(PERFIL, {"telefono": "3101112233"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.telefono, "3101112233")

    def test_perfil_conserva_el_telefono_si_no_se_envia(self):
        self.client.patch(PERFIL, {"nombre_completo": "Tel Perfil Cambiado"}, format="json")
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.telefono, "3001234567")

    def test_perfil_acepta_telefono_vacio(self):
        self.assertEqual(
            self.client.patch(PERFIL, {"telefono": ""}, format="json").status_code, 200
        )

    def test_perfil_rechaza_telefonos_invalidos(self):
        for telefono in INVALIDOS:
            response = self.client.patch(PERFIL, {"telefono": telefono}, format="json")
            self.assertEqual(response.status_code, 400, telefono)
            self.assertIn("telefono", response.data, telefono)
        # The stored value is never overwritten by a rejected request.
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.telefono, "3001234567")


class TelefonoAdminTests(APITestCase):
    def test_admin_endpoint_rechaza_telefono_invalido(self):
        admin = Usuario.objects.create_superuser(
            email="tel-admin@test.dev",
            password="Admin123*",
            nombre_completo="Admin",
            documento=documento_unico(),
        )
        objetivo = Usuario.objects.create_user(
            email="tel-objetivo@test.dev",
            password="Usuario123*",
            nombre_completo="Objetivo",
            documento=documento_unico(),
        )
        self.client.force_authenticate(user=admin)
        response = self.client.patch(
            f"/api/auth/usuarios/{objetivo.id}/", {"telefono": "300ABC4567"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("telefono", response.data)
