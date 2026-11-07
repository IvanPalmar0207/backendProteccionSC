"""Podcast CRUD and permission tests (S14, S15, S20)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.podcasts.models import Podcast

Usuario = get_user_model()


class PodcastTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )
        self.usuario = Usuario.objects.create_user(
            email="user@test.dev", password="Usuario123*", nombre_completo="User", role="USUARIO"
        )

    def test_published_podcast_is_public_and_playable(self):
        Podcast.objects.create(
            titulo="Episodio",
            descripcion="d",
            audio_url="https://example.com/a.mp3",
            publicado=True,
        )
        response = self.client.get("/api/podcasts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["url_audio"], "https://example.com/a.mp3")

    def test_usuario_cannot_manage_podcasts(self):
        podcast = Podcast.objects.create(titulo="P", descripcion="d")
        self.client.force_authenticate(user=self.usuario)
        self.assertEqual(self.client.delete(f"/api/podcasts/{podcast.id}/").status_code, 403)
        self.assertEqual(
            self.client.post("/api/podcasts/", {"titulo": "X"}, format="json").status_code, 403
        )

    def test_admin_full_crud(self):
        self.client.force_authenticate(user=self.admin)
        created = self.client.post(
            "/api/podcasts/",
            {"titulo": "Nuevo", "descripcion": "d", "audio_url": "https://example.com/b.mp3"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        podcast_id = created.data["id"]
        self.assertEqual(
            self.client.patch(
                f"/api/podcasts/{podcast_id}/", {"titulo": "Editado"}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(self.client.delete(f"/api/podcasts/{podcast_id}/").status_code, 204)
