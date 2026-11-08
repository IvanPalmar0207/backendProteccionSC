"""The state-change response carries the fresh follow-up history (Fase 12, S1)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.tests.factories import documento_unico
from apps.denuncias.models import Denuncia, EstadoChoices

Usuario = get_user_model()


class HistorialInmediatoTests(APITestCase):
    def setUp(self):
        self.duenio = Usuario.objects.create_user(
            email="h-duenio@test.dev",
            password="Usuario123*",
            nombre_completo="Dueño Historial",
            documento=documento_unico(),
            role="USUARIO",
        )
        self.prof = Usuario.objects.create_user(
            email="h-prof@test.dev",
            password="Prof123*",
            nombre_completo="Prof Historial",
            documento=documento_unico(),
            role="PROFESIONAL",
        )
        self.admin = Usuario.objects.create_superuser(
            email="h-admin@test.dev",
            password="Admin123*",
            nombre_completo="Admin Historial",
            documento=documento_unico(),
        )
        self.denuncia = Denuncia.objects.create(
            denunciante=self.duenio,
            modalidad="PUBLICA",
            tipo_situacion="ACOSO",
            descripcion="Descripción de prueba suficientemente larga.",
            profesional_asignado=self.prof,
            estado=EstadoChoices.PENDIENTE,
        )

    def test_cambio_de_estado_devuelve_el_historial_actualizado(self):
        self.client.force_authenticate(user=self.prof)
        response = self.client.post(
            f"/api/denuncias/profesional/{self.denuncia.id}/cambiar_estado/",
            {"estado": "EN_PROCESO", "observacion": "Atendiendo el caso"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["estado"], "EN_PROCESO")
        observaciones = [s["observacion"] for s in response.data["seguimientos"]]
        self.assertIn("Atendiendo el caso", observaciones)
        # No duplicate entries in the returned history.
        self.assertEqual(observaciones.count("Atendiendo el caso"), 1)

    def test_asignacion_admin_devuelve_el_historial_actualizado(self):
        pendiente = Denuncia.objects.create(
            denunciante=self.duenio,
            modalidad="PUBLICA",
            tipo_situacion="ACOSO",
            descripcion="Descripción de prueba suficientemente larga.",
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/denuncias/admin/{pendiente.id}/asignar/",
            {"profesional": self.prof.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            any("asignado" in s["observacion"].lower() for s in response.data["seguimientos"])
        )
