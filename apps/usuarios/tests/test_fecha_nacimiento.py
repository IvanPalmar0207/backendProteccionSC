"""Birth-date validation: minimum age 10 and no future dates (Fase 12)."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.core.tests.factories import documento_unico

Usuario = get_user_model()
PERFIL = "/api/perfiles/mi-perfil/"


def hace_anios(anios: int, *, dias: int = 0) -> date:
    """Date ``anios`` years ago (handles 29 February safely)."""
    hoy = date.today()
    try:
        objetivo = hoy.replace(year=hoy.year - anios)
    except ValueError:
        objetivo = hoy.replace(year=hoy.year - anios, day=28)
    return objetivo + timedelta(days=dias)


class FechaNacimientoPerfilTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email="fecha@test.dev",
            password="Usuario123*",
            nombre_completo="Fecha Nacimiento",
            documento=documento_unico(),
        )
        self.client.force_authenticate(user=self.usuario)

    def _enviar(self, fecha):
        return self.client.patch(PERFIL, {"fecha_nacimiento": fecha}, format="json")

    def test_persona_de_9_anios_es_rechazada(self):
        response = self._enviar(hace_anios(9).isoformat())
        self.assertEqual(response.status_code, 400)
        self.assertIn("fecha_nacimiento", response.data)

    def test_persona_de_10_anios_cumplidos_es_permitida(self):
        self.assertEqual(self._enviar(hace_anios(10).isoformat()).status_code, 200)

    def test_persona_de_11_anios_es_permitida(self):
        self.assertEqual(self._enviar(hace_anios(11).isoformat()).status_code, 200)

    def test_fecha_de_ayer_es_rechazada(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        self.assertEqual(self._enviar(ayer).status_code, 400)

    def test_fecha_futura_es_rechazada(self):
        manana = (date.today() + timedelta(days=1)).isoformat()
        response = self._enviar(manana)
        self.assertEqual(response.status_code, 400)
        self.assertIn("fecha_nacimiento", response.data)

    def test_fecha_inexistente_es_rechazada(self):
        self.assertEqual(self._enviar("2020-02-30").status_code, 400)

    def test_cumple_exactamente_10_anios_hoy_es_permitida(self):
        self.assertEqual(self._enviar(hace_anios(10).isoformat()).status_code, 200)

    def test_todavia_no_cumple_10_anios_es_rechazada(self):
        # Turns 10 tomorrow: still 9 today.
        self.assertEqual(self._enviar(hace_anios(10, dias=1).isoformat()).status_code, 400)

    def test_fecha_nula_es_permitida(self):
        # The frontend clears the optional field with ``null``.
        self.assertEqual(self._enviar(None).status_code, 200)

    def test_no_se_guarda_una_fecha_invalida(self):
        original = self.usuario.fecha_nacimiento
        self._enviar(hace_anios(9).isoformat())
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.fecha_nacimiento, original)


class FechaNacimientoModeloTests(APITestCase):
    def test_el_modelo_rechaza_a_un_menor_de_10(self):
        candidato = Usuario(
            email="modelo-menor@test.dev",
            nombre_completo="Modelo Menor",
            documento=documento_unico(),
            fecha_nacimiento=hace_anios(9),
        )
        with self.assertRaises(ValidationError):
            candidato.full_clean(exclude=["password"])

    def test_el_modelo_rechaza_una_fecha_futura(self):
        candidato = Usuario(
            email="modelo-futuro@test.dev",
            nombre_completo="Modelo Futuro",
            documento=documento_unico(),
            fecha_nacimiento=date.today() + timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            candidato.full_clean(exclude=["password"])
