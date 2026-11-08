"""News CRUD, category and image upload tests (S14, S15, F2-S09, F2-S14)."""

import shutil
import tempfile

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.core.tests.factories import archivo_falso, imagen_png
from apps.noticias.models import Noticia

Usuario = get_user_model()


class NoticiaTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(documento=documento_unico(), 
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )
        self.usuario = Usuario.objects.create_user(documento=documento_unico(), 
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

    def test_filter_by_category(self):
        Noticia.objects.create(titulo="A", contenido="c", categoria="PREVENCION")
        Noticia.objects.create(titulo="B", contenido="c", categoria="COMUNIDAD")
        response = self.client.get("/api/noticias/?categoria=PREVENCION")
        self.assertEqual(response.data["count"], 1)

    def test_admin_filter_by_publication_state(self):
        Noticia.objects.create(titulo="Publicada", contenido="c", publicado=True)
        Noticia.objects.create(titulo="Borrador", contenido="c", publicado=False)
        self.client.force_authenticate(user=self.admin)
        publicadas = self.client.get("/api/noticias/?publicado=true")
        self.assertEqual(publicadas.data["count"], 1)
        self.assertEqual(publicadas.data["results"][0]["titulo"], "Publicada")
        borradores = self.client.get("/api/noticias/?publicado=false")
        self.assertEqual(borradores.data["count"], 1)
        self.assertEqual(borradores.data["results"][0]["titulo"], "Borrador")

    def test_admin_combines_search_and_publication_state(self):
        Noticia.objects.create(titulo="Salud pública", contenido="c", publicado=True)
        Noticia.objects.create(titulo="Salud borrador", contenido="c", publicado=False)
        Noticia.objects.create(titulo="Otra", contenido="c", publicado=True)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/noticias/", {"search": "Salud", "publicado": "false"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["titulo"], "Salud borrador")

    def test_public_ignores_publication_filter(self):
        Noticia.objects.create(titulo="Borrador", contenido="c", publicado=False)
        # A non-admin cannot reach drafts even when explicitly asking for them.
        self.assertEqual(self.client.get("/api/noticias/?publicado=false").data["count"], 0)

    def test_usuario_cannot_create_news(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.post(
            "/api/noticias/", {"titulo": "X", "contenido": "Y"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_full_crud(self):
        self.client.force_authenticate(user=self.admin)
        created = self.client.post(
            "/api/noticias/",
            {"titulo": "Nueva", "contenido": "Contenido", "categoria": "DERECHOS"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["categoria_etiqueta"], "Derechos y rutas")
        noticia_id = created.data["id"]

        updated = self.client.patch(
            f"/api/noticias/{noticia_id}/", {"titulo": "Editada"}, format="json"
        )
        self.assertEqual(updated.data["titulo"], "Editada")
        self.assertEqual(self.client.delete(f"/api/noticias/{noticia_id}/").status_code, 204)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class NoticiaImagenTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._overridden_settings["MEDIA_ROOT"], ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(documento=documento_unico(), 
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )
        self.client.force_authenticate(user=self.admin)

    def _crear(self, **extra):
        datos = {"titulo": "Con portada", "contenido": "Contenido", **extra}
        return self.client.post("/api/noticias/", datos, format="multipart")

    def test_uploads_valid_image(self):
        response = self._crear(imagen=imagen_png())
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["imagen"])
        self.assertEqual(Noticia.objects.get().imagen.name.startswith("noticias/"), True)

    def test_rejects_invalid_extension(self):
        response = self._crear(imagen=archivo_falso("malicioso.txt", b"x"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("imagen", response.data)
        self.assertEqual(Noticia.objects.count(), 0)

    def test_rejects_fake_image_bytes(self):
        response = self._crear(imagen=archivo_falso("falsa.png", b"not-an-image"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("imagen", response.data)

    def test_replacing_image_deletes_previous_file(self):
        creada = self._crear(imagen=imagen_png("primera.png"))
        noticia = Noticia.objects.get(id=creada.data["id"])
        archivo_anterior = noticia.imagen.path

        response = self.client.patch(
            f"/api/noticias/{noticia.id}/",
            {"imagen": imagen_png("segunda.png")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)

        import os

        self.assertFalse(os.path.exists(archivo_anterior))
        noticia.refresh_from_db()
        self.assertIn("segunda", noticia.imagen.name)

    def test_clearing_image_with_null(self):
        creada = self._crear(imagen=imagen_png())
        noticia = Noticia.objects.get(id=creada.data["id"])
        response = self.client.patch(
            f"/api/noticias/{noticia.id}/", {"imagen": None}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        noticia.refresh_from_db()
        self.assertFalse(noticia.imagen)

    def test_usuario_cannot_upload(self):
        usuario = Usuario.objects.create_user(documento=documento_unico(), 
            email="user@test.dev", password="Usuario123*", nombre_completo="User", role="USUARIO"
        )
        self.client.force_authenticate(user=usuario)
        response = self._crear(imagen=imagen_png())
        self.assertEqual(response.status_code, 403)
