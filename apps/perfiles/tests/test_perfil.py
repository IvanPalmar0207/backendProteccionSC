"""Profile isolation and validation tests (S9, S20)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

Usuario = get_user_model()


class PerfilTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email="perfil@test.dev",
            password="Usuario123*",
            nombre_completo="Perfil Propio",
            telefono="3000000000",
            role="USUARIO",
        )
        self.otro = Usuario.objects.create_user(
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
