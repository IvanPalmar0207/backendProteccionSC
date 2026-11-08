"""The date of the events can never be in the future (Fase 11, S1)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.core.tests.factories import documento_unico

Usuario = get_user_model()
CREAR = "/api/denuncias/mis-denuncias/"


class FechaHechosTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email="fechas@test.dev",
            password="Usuario123*",
            nombre_completo="Fechas Sucesos",
            documento=documento_unico(),
            role="USUARIO",
        )
        self.client.force_authenticate(user=self.usuario)

    def _crear(self, fecha):
        return self.client.post(
            CREAR,
            {
                "modalidad": "PUBLICA",
                "tipo_situacion": "ACOSO",
                "descripcion": "Descripción de prueba suficientemente larga.",
                "fecha_hechos": fecha,
            },
            format="json",
        )

    def test_fecha_de_ayer_es_permitida(self):
        ayer = (timezone.localdate() - timedelta(days=1)).isoformat()
        self.assertEqual(self._crear(ayer).status_code, 201)

    def test_fecha_de_hoy_es_permitida(self):
        self.assertEqual(self._crear(timezone.localdate().isoformat()).status_code, 201)

    def test_fecha_de_manana_es_rechazada(self):
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        response = self._crear(manana)
        self.assertEqual(response.status_code, 400)
        self.assertIn("fecha_hechos", response.data)

    def test_fecha_futura_de_otro_mes_es_rechazada(self):
        futuro = timezone.localdate().replace(year=timezone.localdate().year + 1).isoformat()
        response = self._crear(futuro)
        self.assertEqual(response.status_code, 400)
        self.assertIn("fecha_hechos", response.data)

    def test_fecha_inexistente_es_rechazada(self):
        self.assertEqual(self._crear("2020-02-30").status_code, 400)

    def test_fecha_omitida_es_permitida(self):
        response = self.client.post(
            CREAR,
            {
                "modalidad": "PUBLICA",
                "tipo_situacion": "ACOSO",
                "descripcion": "Descripción de prueba suficientemente larga.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
