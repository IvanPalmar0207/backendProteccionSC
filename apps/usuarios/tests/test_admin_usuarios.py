"""Administrator user-management and privilege-escalation tests (S7, S20.3, S20.4)."""

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from rest_framework.test import APITestCase

Usuario = get_user_model()


class AdminUsuarioTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(documento=documento_unico(), 
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )
        self.usuario = Usuario.objects.create_user(documento=documento_unico(), 
            email="user@test.dev", password="Usuario123*", nombre_completo="User", role="USUARIO"
        )
        self.profesional = Usuario.objects.create_user(documento=documento_unico(), 
            email="prof@test.dev", password="Prof123*", nombre_completo="Prof", role="PROFESIONAL"
        )

    def test_usuario_cannot_list_accounts(self):
        self.client.force_authenticate(user=self.usuario)
        self.assertEqual(self.client.get("/api/auth/usuarios/").status_code, 403)

    def test_profesional_cannot_list_accounts(self):
        self.client.force_authenticate(user=self.profesional)
        self.assertEqual(self.client.get("/api/auth/usuarios/").status_code, 403)

    def test_profesional_cannot_self_assign_admin(self):
        self.client.force_authenticate(user=self.profesional)
        response = self.client.patch(
            f"/api/auth/usuarios/{self.profesional.id}/",
            {"role": "ADMINISTRADOR"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.profesional.refresh_from_db()
        self.assertEqual(self.profesional.role, "PROFESIONAL")

    def test_admin_can_change_role(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/auth/usuarios/{self.usuario.id}/",
            {"role": "PROFESIONAL"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.role, "PROFESIONAL")

    def test_admin_can_deactivate_account(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/auth/usuarios/{self.usuario.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)

    def test_admin_does_not_appear_in_own_list(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/auth/usuarios/")
        ids = [usuario["id"] for usuario in response.data["results"]]
        self.assertNotIn(self.admin.id, ids)
        self.assertIn(self.usuario.id, ids)
        self.assertIn(self.profesional.id, ids)
        self.assertEqual(response.data["count"], 2)

    def test_admin_search_never_returns_self(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/auth/usuarios/", {"search": "admin@test.dev"})
        self.assertEqual(response.data["count"], 0)

    def test_admin_cannot_deactivate_self(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/auth/usuarios/{self.admin.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("is_active", response.data)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_cannot_change_own_state_either_direction(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/auth/usuarios/{self.admin.id}/", {"is_active": True}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_active)

    def test_admin_cannot_change_document_through_admin_endpoint(self):
        self.usuario.documento = "CC-100"
        self.usuario.save(update_fields=["documento"])
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/auth/usuarios/{self.usuario.id}/",
            {"documento": "CC-999"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("documento", response.data)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.documento, "CC-100")

    def test_admin_can_still_edit_own_profile(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            "/api/perfiles/mi-perfil/", {"telefono": "3001112222"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.telefono, "3001112222")
