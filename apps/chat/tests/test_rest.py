"""REST chat permission and flow tests (HU-06, S7, S13)."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.chat.models import Conversacion, Mensaje
from apps.denuncias.models import Denuncia, ModalidadChoices, TipoSituacionChoices

Usuario = get_user_model()


class ChatRestTests(APITestCase):
    def setUp(self):
        self.duenio = Usuario.objects.create_user(
            email="duenio@test.dev", password="Usuario123*", nombre_completo="Dueña", role="USUARIO"
        )
        self.profesional = Usuario.objects.create_user(
            email="prof@test.dev", password="Prof123*", nombre_completo="Profesional", role="PROFESIONAL"
        )
        self.otro = Usuario.objects.create_user(
            email="otro@test.dev", password="Usuario123*", nombre_completo="Otra", role="USUARIO"
        )
        self.admin = Usuario.objects.create_superuser(
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )
        self.denuncia = Denuncia.objects.create(
            denunciante=self.duenio,
            modalidad=ModalidadChoices.ANONIMA,
            tipo_situacion=TipoSituacionChoices.ACOSO,
            descripcion="Descripción de prueba suficientemente larga.",
            profesional_asignado=self.profesional,
        )
        self.conversacion = Conversacion.objects.create(denuncia=self.denuncia)
        self.conversacion.participantes.add(self.duenio, self.profesional)

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_list_only_includes_own_conversations(self):
        self._auth(self.otro)
        response = self.client.get("/api/chat/conversaciones/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_participant_can_list(self):
        self._auth(self.duenio)
        response = self.client.get("/api/chat/conversaciones/")
        self.assertEqual(response.data["count"], 1)

    def test_non_participant_cannot_retrieve(self):
        self._auth(self.otro)
        response = self.client.get(f"/api/chat/conversaciones/{self.conversacion.id}/")
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_retrieve_private_chat(self):
        self._auth(self.admin)
        response = self.client.get(f"/api/chat/conversaciones/{self.conversacion.id}/")
        self.assertEqual(response.status_code, 403)
        response = self.client.get(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/"
        )
        self.assertEqual(response.status_code, 403)

    def test_non_participant_cannot_post_message(self):
        self._auth(self.otro)
        response = self.client.post(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/",
            {"contenido": "intruso"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Mensaje.objects.count(), 0)

    def test_participant_posts_and_marks_read(self):
        self._auth(self.duenio)
        response = self.client.post(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/",
            {"contenido": "Necesito ayuda"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Mensaje.objects.count(), 1)

        self._auth(self.profesional)
        response = self.client.get(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/"
        )
        self.assertEqual(response.data["count"], 1)
        response = self.client.post(
            f"/api/chat/conversaciones/{self.conversacion.id}/marcar_leidos/"
        )
        self.assertEqual(response.data["actualizados"], 1)
        self.assertTrue(Mensaje.objects.first().leido)

    def test_empty_message_is_rejected(self):
        self._auth(self.duenio)
        response = self.client.post(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/",
            {"contenido": "   "},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Mensaje.objects.count(), 0)

    def test_owner_creates_conversation(self):
        denuncia = Denuncia.objects.create(
            denunciante=self.duenio,
            modalidad=ModalidadChoices.PUBLICA,
            tipo_situacion=TipoSituacionChoices.ABUSO,
            descripcion="Otra descripción suficientemente larga.",
        )
        self._auth(self.duenio)
        response = self.client.post(
            "/api/chat/conversaciones/", {"denuncia": denuncia.id}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["denuncia"]["id"], denuncia.id)

    def test_other_user_cannot_open_conversation(self):
        self._auth(self.otro)
        response = self.client.post(
            "/api/chat/conversaciones/", {"denuncia": self.denuncia.id}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_open_conversation(self):
        self._auth(self.admin)
        response = self.client.post(
            "/api/chat/conversaciones/", {"denuncia": self.denuncia.id}, format="json"
        )
        self.assertEqual(response.status_code, 403)
