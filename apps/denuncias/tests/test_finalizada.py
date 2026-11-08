"""A finished report is read-only: writes are rejected with 409 (Fase 12, S2)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.chat.models import Conversacion, Mensaje
from apps.core.tests.factories import documento_unico
from apps.denuncias.models import Denuncia, EstadoChoices

Usuario = get_user_model()


class DenunciaFinalizadaTests(APITestCase):
    def setUp(self):
        self.duenio = Usuario.objects.create_user(
            email="fin-duenio@test.dev",
            password="Usuario123*",
            nombre_completo="Dueño Fin",
            documento=documento_unico(),
            role="USUARIO",
        )
        self.prof = Usuario.objects.create_user(
            email="fin-prof@test.dev",
            password="Prof123*",
            nombre_completo="Prof Fin",
            documento=documento_unico(),
            role="PROFESIONAL",
        )
        self.admin = Usuario.objects.create_superuser(
            email="fin-admin@test.dev",
            password="Admin123*",
            nombre_completo="Admin Fin",
            documento=documento_unico(),
        )
        self.denuncia = Denuncia.objects.create(
            denunciante=self.duenio,
            modalidad="PUBLICA",
            tipo_situacion="ACOSO",
            descripcion="Descripción de prueba suficientemente larga.",
            profesional_asignado=self.prof,
            estado=EstadoChoices.FINALIZADA,
        )
        self.conversacion = Conversacion.objects.create(denuncia=self.denuncia)
        self.conversacion.participantes.set([self.duenio, self.prof])
        Mensaje.objects.create(
            conversacion=self.conversacion, remitente=self.duenio, contenido="Historial previo"
        )

    def test_no_permite_cambiar_el_estado(self):
        self.client.force_authenticate(user=self.prof)
        response = self.client.post(
            f"/api/denuncias/profesional/{self.denuncia.id}/cambiar_estado/",
            {"estado": "EN_PROCESO"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.denuncia.refresh_from_db()
        self.assertEqual(self.denuncia.estado, EstadoChoices.FINALIZADA)

    def test_el_admin_no_puede_reasignar_una_finalizada(self):
        otro = Usuario.objects.create_user(
            email="fin-prof2@test.dev",
            password="Prof123*",
            nombre_completo="Prof Dos Fin",
            documento=documento_unico(),
            role="PROFESIONAL",
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/denuncias/admin/{self.denuncia.id}/asignar/",
            {"profesional": otro.id},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.denuncia.refresh_from_db()
        self.assertEqual(self.denuncia.profesional_asignado_id, self.prof.id)

    def test_no_permite_enviar_mensajes_por_rest(self):
        self.client.force_authenticate(user=self.prof)
        response = self.client.post(
            f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/",
            {"contenido": "no permitido"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Mensaje.objects.count(), 1)

    def test_permite_consultar_detalle_historial_y_mensajes(self):
        self.client.force_authenticate(user=self.duenio)
        self.assertEqual(
            self.client.get(f"/api/denuncias/mis-denuncias/{self.denuncia.id}/").status_code, 200
        )
        self.assertEqual(
            self.client.get(f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/").status_code,
            200,
        )
        # The professional also keeps read access.
        self.client.force_authenticate(user=self.prof)
        self.assertEqual(
            self.client.get(f"/api/denuncias/profesional/{self.denuncia.id}/").status_code, 200
        )
        self.assertEqual(
            self.client.get(f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/").data["count"],
            1,
        )
