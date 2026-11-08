"""Cover image upload tests for podcasts (F2-S10, F2-S14)."""

import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.core.tests.factories import archivo_falso, imagen_png
from apps.podcasts.models import Podcast

Usuario = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PodcastPortadaTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._overridden_settings["MEDIA_ROOT"], ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(documento=documento_unico(), 
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )
        self.client.force_authenticate(user=self.admin)

    def test_uploads_and_replaces_cover(self):
        creado = self.client.post(
            "/api/podcasts/",
            {
                "titulo": "Episodio",
                "enlace": "https://open.spotify.com/episode/1",
                "portada": imagen_png("uno.png"),
            },
            format="multipart",
        )
        self.assertEqual(creado.status_code, 201)
        podcast = Podcast.objects.get()
        anterior = podcast.portada.path
        self.assertTrue(os.path.exists(anterior))

        actualizado = self.client.patch(
            f"/api/podcasts/{podcast.id}/",
            {"portada": imagen_png("dos.png")},
            format="multipart",
        )
        self.assertEqual(actualizado.status_code, 200)
        self.assertFalse(os.path.exists(anterior))
        podcast.refresh_from_db()
        self.assertIn("dos", podcast.portada.name)

    def test_rejects_non_image_cover(self):
        respuesta = self.client.post(
            "/api/podcasts/",
            {
                "titulo": "Episodio",
                "enlace": "https://open.spotify.com/episode/2",
                "portada": archivo_falso("falsa.png", b"nope"),
            },
            format="multipart",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("portada", respuesta.data)
