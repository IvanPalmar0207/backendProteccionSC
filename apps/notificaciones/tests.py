"""Notification isolation and chat-notification tests (Fase 8, S9, S11)."""

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from rest_framework.test import APITestCase

from apps.chat.models import Conversacion
from apps.denuncias.models import Denuncia, ModalidadChoices, TipoSituacionChoices
from apps.notificaciones.models import Notificacion, TipoNotificacionChoices
from apps.notificaciones.services import notificar

Usuario = get_user_model()


class NotificacionBase(APITestCase):
    def setUp(self):
        self.duenio = Usuario.objects.create_user(documento=documento_unico(), 
            email="noti-duenio@test.dev",
            password="Usuario123*",
            nombre_completo="Dueña Noti",
            role="USUARIO",
        )
        self.profesional = Usuario.objects.create_user(documento=documento_unico(), 
            email="noti-prof@test.dev",
            password="Prof123*",
            nombre_completo="Prof Noti",
            role="PROFESIONAL",
        )
        self.otro = Usuario.objects.create_user(documento=documento_unico(), 
            email="noti-otro@test.dev",
            password="Usuario123*",
            nombre_completo="Otra Noti",
            role="USUARIO",
        )
        self.admin = Usuario.objects.create_superuser(documento=documento_unico(), 
            email="noti-admin@test.dev", password="Admin123*", nombre_completo="Admin Noti"
        )


class NotificacionAislamientoTests(NotificacionBase):
    def test_user_only_lists_own_notifications(self):
        notificar(self.duenio, "Para la dueña")
        notificar(self.otro, "Para otra")
        self.client.force_authenticate(user=self.duenio)
        respuesta = self.client.get("/api/notificaciones/")
        self.assertEqual(respuesta.data["count"], 1)
        self.assertEqual(respuesta.data["results"][0]["titulo"], "Para la dueña")

    def test_user_cannot_retrieve_foreign_notification(self):
        ajena = notificar(self.otro, "Privada")
        self.client.force_authenticate(user=self.duenio)
        respuesta = self.client.get(f"/api/notificaciones/{ajena.id}/")
        self.assertEqual(respuesta.status_code, 404)

    def test_unread_count_is_per_user(self):
        notificar(self.duenio, "A", tipo=TipoNotificacionChoices.SISTEMA)
        notificar(self.duenio, "B", tipo=TipoNotificacionChoices.SISTEMA)
        notificar(self.otro, "C", tipo=TipoNotificacionChoices.SISTEMA)
        self.client.force_authenticate(user=self.duenio)
        self.assertEqual(self.client.get("/api/notificaciones/no_leidas/").data["no_leidas"], 2)
        self.client.force_authenticate(user=self.otro)
        self.assertEqual(self.client.get("/api/notificaciones/no_leidas/").data["no_leidas"], 1)

    def test_mark_one_and_all_as_read(self):
        primera = notificar(self.duenio, "Uno")
        notificar(self.duenio, "Dos")
        self.client.force_authenticate(user=self.duenio)
        self.client.post(f"/api/notificaciones/{primera.id}/marcar_leida/")
        self.assertEqual(self.client.get("/api/notificaciones/no_leidas/").data["no_leidas"], 1)
        self.client.post("/api/notificaciones/marcar_todas_leidas/")
        self.assertEqual(self.client.get("/api/notificaciones/no_leidas/").data["no_leidas"], 0)

    def test_marking_a_foreign_notification_is_not_possible(self):
        ajena = notificar(self.otro, "No tuya")
        self.client.force_authenticate(user=self.duenio)
        respuesta = self.client.post(f"/api/notificaciones/{ajena.id}/marcar_leida/")
        self.assertEqual(respuesta.status_code, 404)
        ajena.refresh_from_db()
        self.assertFalse(ajena.leida)


class NotificacionMensajeTests(NotificacionBase):
    def setUp(self):
        super().setUp()
        self.denuncia = Denuncia.objects.create(
            denunciante=self.duenio,
            modalidad=ModalidadChoices.ANONIMA,
            tipo_situacion=TipoSituacionChoices.ACOSO,
            descripcion="Descripción de prueba suficientemente larga.",
            profesional_asignado=self.profesional,
        )
        self.conversacion = Conversacion.objects.create(denuncia=self.denuncia)
        self.conversacion.participantes.add(self.duenio, self.profesional)

    def test_message_notifies_the_other_participant_not_the_sender(self):
        self.client.force_authenticate(user=self.duenio)
        respuesta = self.client.post(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/",
            {"contenido": "Hola profesional"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(
            Notificacion.objects.filter(usuario=self.profesional, tipo="MENSAJE").count(), 1
        )
        self.assertEqual(
            Notificacion.objects.filter(usuario=self.duenio, tipo="MENSAJE").count(), 0
        )

    def test_admin_never_receives_chat_notifications(self):
        # The admin is not a participant, so no message notification can reach it.
        self.client.force_authenticate(user=self.duenio)
        self.client.post(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/",
            {"contenido": "Mensaje para el profesional"},
            format="json",
        )
        self.assertEqual(
            Notificacion.objects.filter(usuario=self.admin, tipo="MENSAJE").count(), 0
        )
