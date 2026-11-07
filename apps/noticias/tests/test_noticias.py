"""News CRUD and permission tests (S14, S15, S20)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.noticias.models import Noticia

Usuario = get_user_model()


class NoticiaTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )
        self.usuario = Usuario.objects.create_user(
            email="user@test.dev", password="Usuario123*", nombre_completo="User", role="USUARIO"
        )

    def test_published_news_is_public(self):
        Noticia.objects.create(titulo="Pública", contenido="c", publicado=True)
        response = self.client.get("/api/noticias/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_draft_is_hidden_from_public(self):
        Noticia.objects.create(titulo="Borrador", contenido="c", publicado=False)
        self.assertEqual(self.client.get("/api/noticias/").data["count"], 0)

    def test_usuario_cannot_create_news(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.post(
            "/api/noticias/", {"titulo": "X", "contenido": "Y"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_usuario_cannot_delete_news(self):
        noticia = Noticia.objects.create(titulo="N", contenido="c")
        self.client.force_authenticate(user=self.usuario)
        self.assertEqual(self.client.delete(f"/api/noticias/{noticia.id}/").status_code, 403)

    def test_admin_full_crud(self):
        self.client.force_authenticate(user=self.admin)
        created = self.client.post(
            "/api/noticias/", {"titulo": "Nueva", "contenido": "Contenido"}, format="json"
        )
        self.assertEqual(created.status_code, 201)
        noticia_id = created.data["id"]

        updated = self.client.patch(
            f"/api/noticias/{noticia_id}/", {"titulo": "Editada"}, format="json"
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["titulo"], "Editada")

        self.assertEqual(self.client.get(f"/api/noticias/{noticia_id}/").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/noticias/{noticia_id}/").status_code, 204)
        self.assertFalse(Noticia.objects.filter(id=noticia_id).exists())
