"""Podcast CRUD, permission and external-link validation tests (S14, S15, F2-S10)."""

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

    def test_published_podcast_is_public_and_exposes_external_link(self):
        Podcast.objects.create(
            titulo="Episodio",
            descripcion="d",
            programa="Programa",
            plataforma="SPOTIFY",
            enlace="https://open.spotify.com/episode/abc",
            publicado=True,
        )
        response = self.client.get("/api/podcasts/")
        self.assertEqual(response.status_code, 200)
        episodio = response.data["results"][0]
        self.assertEqual(episodio["enlace"], "https://open.spotify.com/episode/abc")
        self.assertEqual(episodio["plataforma_etiqueta"], "Spotify")

    def test_draft_is_hidden_from_public(self):
        Podcast.objects.create(titulo="Borrador", enlace="https://example.com/a", publicado=False)
        self.assertEqual(self.client.get("/api/podcasts/").data["count"], 0)

    def test_usuario_cannot_manage_podcasts(self):
        podcast = Podcast.objects.create(titulo="P", enlace="https://example.com/a")
        self.client.force_authenticate(user=self.usuario)
        self.assertEqual(self.client.delete(f"/api/podcasts/{podcast.id}/").status_code, 403)
        self.assertEqual(
            self.client.post("/api/podcasts/", {"titulo": "X"}, format="json").status_code, 403
        )

    def test_admin_can_create_episode_with_external_link(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/podcasts/",
            {
                "titulo": "Nuevo",
                "programa": "Voces",
                "plataforma": "YOUTUBE",
                "enlace": "https://www.youtube.com/watch?v=abc",
                "publicado": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["plataforma_etiqueta"], "YouTube")

    def test_https_is_required(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/podcasts/",
            {"titulo": "Inseguro", "enlace": "http://example.com/a.mp3"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("enlace", response.data)

    def test_link_is_required(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/podcasts/", {"titulo": "Sin enlace"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("enlace", response.data)

    def test_invalid_url_is_rejected(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/podcasts/", {"titulo": "Malo", "enlace": "no-es-url"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("enlace", response.data)

    def test_admin_full_crud(self):
        self.client.force_authenticate(user=self.admin)
        created = self.client.post(
            "/api/podcasts/",
            {"titulo": "Nuevo", "enlace": "https://example.com/ep", "publicado": True},
            format="json",
        )
        podcast_id = created.data["id"]
        self.assertEqual(
            self.client.patch(
                f"/api/podcasts/{podcast_id}/", {"titulo": "Editado"}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(self.client.delete(f"/api/podcasts/{podcast_id}/").status_code, 204)
        self.assertFalse(Podcast.objects.filter(id=podcast_id).exists())
