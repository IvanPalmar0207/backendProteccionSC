"""Podcast CRUD, permission and external-link validation tests (S14, S15, F2-S10)."""

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from rest_framework.test import APITestCase

from apps.podcasts.models import Podcast

Usuario = get_user_model()


class PodcastTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(documento=documento_unico(), 
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )
        self.usuario = Usuario.objects.create_user(documento=documento_unico(), 
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

    def test_admin_filter_by_publication_state(self):
        Podcast.objects.create(
            titulo="Publicado", enlace="https://example.com/a", publicado=True
        )
        Podcast.objects.create(
            titulo="Borrador", enlace="https://example.com/b", publicado=False
        )
        self.client.force_authenticate(user=self.admin)
        publicados = self.client.get("/api/podcasts/?publicado=true")
        self.assertEqual(publicados.data["count"], 1)
        self.assertEqual(publicados.data["results"][0]["titulo"], "Publicado")
        borradores = self.client.get("/api/podcasts/?publicado=false")
        self.assertEqual(borradores.data["count"], 1)
        self.assertEqual(borradores.data["results"][0]["titulo"], "Borrador")

    def test_admin_combines_search_and_publication_state(self):
        Podcast.objects.create(titulo="Salud pública", enlace="https://example.com/a", publicado=True)
        Podcast.objects.create(titulo="Salud borrador", enlace="https://example.com/b", publicado=False)
        Podcast.objects.create(titulo="Otra", enlace="https://example.com/c", publicado=True)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/podcasts/", {"search": "Salud", "publicado": "false"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["titulo"], "Salud borrador")

    def test_public_ignores_publication_filter(self):
        Podcast.objects.create(
            titulo="Borrador", enlace="https://example.com/b", publicado=False
        )
        self.assertEqual(self.client.get("/api/podcasts/?publicado=false").data["count"], 0)

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
