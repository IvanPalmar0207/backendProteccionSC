"""Chat access after a professional reassignment (Fase 11, S6)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.chat.models import Conversacion, Mensaje
from apps.core.tests.factories import documento_unico
from apps.denuncias.models import Denuncia, ModalidadChoices, TipoSituacionChoices

Usuario = get_user_model()


class ChatReasignacionTests(APITestCase):
    def setUp(self):
        self.duenio = Usuario.objects.create_user(
            email="rea-duenio@test.dev",
            password="Usuario123*",
            nombre_completo="Dueña Rea",
            documento=documento_unico(),
            role="USUARIO",
        )
        self.p1 = Usuario.objects.create_user(
            email="rea-p1@test.dev",
            password="Prof123*",
            nombre_completo="Prof Uno",
            documento=documento_unico(),
            role="PROFESIONAL",
        )
        self.p2 = Usuario.objects.create_user(
            email="rea-p2@test.dev",
            password="Prof123*",
            nombre_completo="Prof Dos",
            documento=documento_unico(),
            role="PROFESIONAL",
        )
        self.admin = Usuario.objects.create_superuser(
            email="rea-admin@test.dev",
            password="Admin123*",
            nombre_completo="Admin Rea",
            documento=documento_unico(),
        )
        self.denuncia = Denuncia.objects.create(
            denunciante=self.duenio,
            modalidad=ModalidadChoices.PUBLICA,
            tipo_situacion=TipoSituacionChoices.ACOSO,
            descripcion="Descripción de prueba suficientemente larga.",
            profesional_asignado=self.p1,
        )
        self.conversacion = Conversacion.objects.create(denuncia=self.denuncia)
        self.conversacion.participantes.set([self.duenio, self.p1])
        Mensaje.objects.create(
            conversacion=self.conversacion, remitente=self.duenio, contenido="Hola"
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _reasignar(self, profesional):
        self._auth(self.admin)
        return self.client.post(
            f"/api/denuncias/admin/{self.denuncia.id}/asignar/",
            {"profesional": profesional.id},
            format="json",
        )

    def test_el_profesional_anterior_pierde_el_acceso(self):
        self.assertEqual(self._reasignar(self.p2).status_code, 200)
        self._auth(self.p1)
        conv = self.conversacion.id
        self.assertEqual(self.client.get(f"/api/chat/conversaciones/{conv}/").status_code, 403)
        self.assertEqual(
            self.client.get(f"/api/chat/conversaciones/{conv}/mensajes/").status_code, 403
        )
        self.assertEqual(
            self.client.post(
                f"/api/chat/conversaciones/{conv}/mensajes/",
                {"contenido": "intruso"},
                format="json",
            ).status_code,
            403,
        )

    def test_el_nuevo_profesional_obtiene_acceso(self):
        self._reasignar(self.p2)
        self._auth(self.p2)
        conv = self.conversacion.id
        self.assertEqual(self.client.get(f"/api/chat/conversaciones/{conv}/").status_code, 200)
        response = self.client.post(
            f"/api/chat/conversaciones/{conv}/mensajes/",
            {"contenido": "Hola, tomo el caso"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_el_duenio_conserva_el_acceso_y_el_historial(self):
        self._reasignar(self.p2)
        self._auth(self.duenio)
        conv = self.conversacion.id
        self.assertEqual(self.client.get(f"/api/chat/conversaciones/{conv}/").status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/chat/conversaciones/{conv}/mensajes/").data["count"], 1
        )
        self.assertEqual(Mensaje.objects.filter(conversacion=self.conversacion).count(), 1)

    def test_el_administrador_no_abre_conversaciones(self):
        # Even as the report's author (unreachable via the API), an admin is
        # never allowed to open a private chat.
        denuncia = Denuncia.objects.create(
            denunciante=self.admin,
            modalidad=ModalidadChoices.PUBLICA,
            tipo_situacion=TipoSituacionChoices.ACOSO,
            descripcion="Descripción de prueba suficientemente larga.",
            profesional_asignado=self.p1,
        )
        self._auth(self.admin)
        response = self.client.post(
            "/api/chat/conversaciones/", {"denuncia": denuncia.id}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_el_administrador_no_lee_el_chat(self):
        self._auth(self.admin)
        self.assertEqual(
            self.client.get(f"/api/chat/conversaciones/{self.conversacion.id}/").status_code,
            403,
        )
