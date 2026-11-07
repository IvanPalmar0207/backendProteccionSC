"""Forum CRUD and permission tests (S14, S15, S20)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.foro.models import Publicacion, Respuesta

Usuario = get_user_model()


class ForoTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )
        self.autor = Usuario.objects.create_user(
            email="autor@test.dev", password="Usuario123*", nombre_completo="Autor", role="USUARIO"
        )
        self.otro = Usuario.objects.create_user(
            email="otro@test.dev", password="Usuario123*", nombre_completo="Otro", role="USUARIO"
        )

    def test_requires_authentication(self):
        self.assertEqual(self.client.get("/api/foro/publicaciones/").status_code, 401)

    def test_authenticated_user_creates_publication_and_reply(self):
        self.client.force_authenticate(user=self.autor)
        created = self.client.post(
            "/api/foro/publicaciones/", {"titulo": "Hilo", "contenido": "Cuerpo"}, format="json"
        )
        self.assertEqual(created.status_code, 201)
        publicacion_id = created.data["id"]

        reply = self.client.post(
            f"/api/foro/publicaciones/{publicacion_id}/responder/",
            {"contenido": "Mi respuesta"},
            format="json",
        )
        self.assertEqual(reply.status_code, 201)
        self.assertEqual(Respuesta.objects.count(), 1)

    def test_non_author_cannot_edit_publication(self):
        publicacion = Publicacion.objects.create(titulo="H", contenido="c", autor=self.autor)
        self.client.force_authenticate(user=self.otro)
        response = self.client.patch(
            f"/api/foro/publicaciones/{publicacion.id}/", {"titulo": "Robado"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_non_author_cannot_delete_reply(self):
        publicacion = Publicacion.objects.create(titulo="H", contenido="c", autor=self.autor)
        respuesta = Respuesta.objects.create(
            publicacion=publicacion, autor=self.autor, contenido="r"
        )
        self.client.force_authenticate(user=self.otro)
        self.assertEqual(
            self.client.delete(f"/api/foro/respuestas/{respuesta.id}/").status_code, 403
        )

    def test_author_can_delete_own_publication(self):
        publicacion = Publicacion.objects.create(titulo="H", contenido="c", autor=self.autor)
        self.client.force_authenticate(user=self.autor)
        self.assertEqual(
            self.client.delete(f"/api/foro/publicaciones/{publicacion.id}/").status_code, 204
        )

    def test_admin_can_manage_any_publication(self):
        publicacion = Publicacion.objects.create(titulo="H", contenido="c", autor=self.autor)
        self.client.force_authenticate(user=self.admin)
        self.assertEqual(
            self.client.patch(
                f"/api/foro/publicaciones/{publicacion.id}/", {"titulo": "Moderado"}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.delete(f"/api/foro/publicaciones/{publicacion.id}/").status_code, 204
        )

    def test_publications_include_replies(self):
        publicacion = Publicacion.objects.create(titulo="H", contenido="c", autor=self.autor)
        Respuesta.objects.create(publicacion=publicacion, autor=self.otro, contenido="r")
        self.client.force_authenticate(user=self.autor)
        response = self.client.get(f"/api/foro/publicaciones/{publicacion.id}/")
        self.assertEqual(response.data["respuestas_count"], 1)
        self.assertEqual(len(response.data["respuestas"]), 1)
