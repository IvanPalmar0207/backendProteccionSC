"""Profile isolation and validation tests (S9, S20)."""

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from rest_framework.test import APITestCase

Usuario = get_user_model()


class PerfilTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email="perfil@test.dev",
            password="Usuario123*",
            nombre_completo="Perfil Propio",
            telefono="3000000000",
            documento="CC-123456",
            role="USUARIO",
        )
        self.otro = Usuario.objects.create_user(documento=documento_unico(), 
            email="otro@test.dev", password="Usuario123*", nombre_completo="Otra", role="USUARIO"
        )

    def test_cannot_read_profile_without_auth(self):
        self.assertEqual(self.client.get("/api/perfiles/mi-perfil/").status_code, 401)

    def test_reads_own_profile(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.get("/api/perfiles/mi-perfil/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "perfil@test.dev")

    def test_updates_own_profile(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.patch(
            "/api/perfiles/mi-perfil/", {"telefono": "3111111111"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.telefono, "3111111111")

    def test_cannot_change_role_through_profile(self):
        self.client.force_authenticate(user=self.usuario)
        self.client.patch(
            "/api/perfiles/mi-perfil/", {"role": "ADMINISTRADOR"}, format="json"
        )
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.role, "USUARIO")

    def test_profile_endpoint_is_not_addressable_by_user_id(self):
        self.client.force_authenticate(user=self.otro)
        # There is no per-id route; the endpoint always resolves request.user.
        self.assertEqual(self.client.get(f"/api/perfiles/{self.usuario.id}/").status_code, 404)

    def test_names_are_required_on_update(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.patch(
            "/api/perfiles/mi-perfil/", {"nombre_completo": ""}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("nombre_completo", response.data)

    def test_document_is_returned_in_the_profile(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.get("/api/perfiles/mi-perfil/")
        self.assertEqual(response.data["documento"], "CC-123456")

    def test_document_cannot_be_changed_with_patch(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.patch(
            "/api/perfiles/mi-perfil/", {"documento": "CC-999999"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("documento", response.data)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.documento, "CC-123456")

    def test_document_cannot_be_changed_with_put(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.put(
            "/api/perfiles/mi-perfil/",
            {"nombre_completo": "Perfil Propio", "documento": "CC-999999"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("documento", response.data)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.documento, "CC-123456")

    def test_document_may_be_resubmitted_unchanged(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.patch(
            "/api/perfiles/mi-perfil/",
            {"documento": "CC-123456", "telefono": "3222222222"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.telefono, "3222222222")

    def test_other_roles_cannot_change_their_document_either(self):
        profesional = Usuario.objects.create_user(
            email="perfil-prof@test.dev",
            password="Prof123*",
            nombre_completo="Perfil Profesional",
            documento="CC-PROF",
            role="PROFESIONAL",
        )
        self.client.force_authenticate(user=profesional)
        response = self.client.patch(
            "/api/perfiles/mi-perfil/", {"documento": "CC-OTRO"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        profesional.refresh_from_db()
        self.assertEqual(profesional.documento, "CC-PROF")
