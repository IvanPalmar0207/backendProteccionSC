"""REST chat permission and flow tests (HU-06, S7, S13)."""

import json

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.chat.models import Conversacion, Mensaje
from apps.denuncias.models import Denuncia, ModalidadChoices, TipoSituacionChoices

Usuario = get_user_model()


class ChatRestTests(APITestCase):
    def setUp(self):
        self.duenio = Usuario.objects.create_user(documento=documento_unico(), 
            email="duenio@test.dev", password="Usuario123*", nombre_completo="Dueña", role="USUARIO"
        )
        self.profesional = Usuario.objects.create_user(documento=documento_unico(), 
            email="prof@test.dev", password="Prof123*", nombre_completo="Profesional", role="PROFESIONAL"
        )
        self.otro = Usuario.objects.create_user(documento=documento_unico(), 
            email="otro@test.dev", password="Usuario123*", nombre_completo="Otra", role="USUARIO"
        )
        self.admin = Usuario.objects.create_superuser(documento=documento_unico(), 
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

    def test_professional_cannot_open_conversation_for_anothers_case(self):
        # ``self.denuncia`` is already assigned to ``self.profesional``.
        otro_prof = Usuario.objects.create_user(documento=documento_unico(), 
            email="prof2@test.dev",
            password="Prof123*",
            nombre_completo="Prof 2",
            role="PROFESIONAL",
        )
        self._auth(otro_prof)
        response = self.client.post(
            "/api/chat/conversaciones/", {"denuncia": self.denuncia.id}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_professional_cannot_open_conversation_for_unassigned_case(self):
        denuncia = Denuncia.objects.create(
            denunciante=self.duenio,
            modalidad=ModalidadChoices.PUBLICA,
            tipo_situacion=TipoSituacionChoices.ABUSO,
            descripcion="Caso sin profesional asignado.",
        )
        self._auth(self.profesional)
        response = self.client.post(
            "/api/chat/conversaciones/", {"denuncia": denuncia.id}, format="json"
        )
        # No professional may open a chat while the case has no assignee.
        self.assertEqual(response.status_code, 403)
        denuncia.refresh_from_db()
        self.assertIsNone(denuncia.profesional_asignado_id)

    def test_anonymous_reporter_name_is_hidden_in_conversation(self):
        self._auth(self.duenio)
        self.client.post(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/",
            {"contenido": "Hola, necesito ayuda"},
            format="json",
        )
        self._auth(self.profesional)
        response = self.client.get(f"/api/chat/conversaciones/{self.conversacion.id}/")
        serialized = response.content.decode()
        self.assertNotIn("Dueña", serialized)
        nombres = {p["id"]: p["nombre_completo"] for p in response.data["participantes"]}
        self.assertEqual(nombres[self.duenio.id], "Denunciante anónimo")
        self.assertEqual(nombres[self.profesional.id], "Profesional")
        self.assertEqual(response.data["ultimo_mensaje"]["remitente_nombre"], "Denunciante anónimo")

    def test_anonymous_reporter_name_is_hidden_in_messages(self):
        self._auth(self.duenio)
        self.client.post(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/",
            {"contenido": "Mensaje de la persona anónima"},
            format="json",
        )
        self._auth(self.profesional)
        response = self.client.get(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/"
        )
        remitentes = [m["remitente"]["nombre_completo"] for m in response.data["results"]]
        self.assertEqual(remitentes, ["Denunciante anónimo"])

    def test_owner_keeps_seeing_own_name(self):
        self._auth(self.duenio)
        response = self.client.get(f"/api/chat/conversaciones/{self.conversacion.id}/")
        nombres = {p["id"]: p["nombre_completo"] for p in response.data["participantes"]}
        self.assertEqual(nombres[self.duenio.id], "Dueña")
