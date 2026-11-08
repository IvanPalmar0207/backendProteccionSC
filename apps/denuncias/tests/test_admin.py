"""The Django admin must not expose the identity of an anonymous reporter."""

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from django.test import TestCase

from apps.denuncias.models import Denuncia, ModalidadChoices, SeguimientoDenuncia, TipoSituacionChoices

Usuario = get_user_model()


class AdminPrivacidadTests(TestCase):
    def setUp(self):
        self.duenio = Usuario.objects.create_user(
            email="anonimo@test.dev",
            password="Sendero#Calido2026",
            nombre_completo="Persona Anonima",
            telefono="3009998877",
            documento="CC-ANONIMO",
            role="USUARIO",
        )
        self.admin = Usuario.objects.create_superuser(documento=documento_unico(), 
            email="admin@test.dev", password="Faro#Seguro2026", nombre_completo="Admin"
        )
        self.denuncia = Denuncia.objects.create(
            denunciante=self.duenio,
            modalidad=ModalidadChoices.ANONIMA,
            tipo_situacion=TipoSituacionChoices.ACOSO,
            descripcion="Relato ficticio de prueba para el admin.",
        )
        SeguimientoDenuncia.objects.create(
            denuncia=self.denuncia, autor=self.duenio, estado_nuevo="PENDIENTE",
            observacion="Denuncia registrada.",
        )
        self.client.force_login(self.admin)

    def test_change_form_does_not_render_reporter_identity(self):
        respuesta = self.client.get(f"/admin/denuncias/denuncia/{self.denuncia.id}/change/")
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode()
        for valor in ["anonimo@test.dev", "Persona Anonima", "3009998877", "CC-ANONIMO"]:
            self.assertNotIn(valor, contenido, f"Fuga de identidad en el admin: {valor}")

    def test_changelist_does_not_render_reporter_identity(self):
        respuesta = self.client.get("/admin/denuncias/denuncia/")
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode()
        for valor in ["anonimo@test.dev", "Persona Anonima", "CC-ANONIMO"]:
            self.assertNotIn(valor, contenido, f"Fuga de identidad en el admin: {valor}")
