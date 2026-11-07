"""Administrator user-management and privilege-escalation tests (S7, S20.3, S20.4)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

Usuario = get_user_model()


class AdminUsuarioTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )
        self.usuario = Usuario.objects.create_user(
            email="user@test.dev", password="Usuario123*", nombre_completo="User", role="USUARIO"
        )
        self.profesional = Usuario.objects.create_user(
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
