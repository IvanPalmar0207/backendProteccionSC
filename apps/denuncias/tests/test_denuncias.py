"""Report isolation, anonymity and state-transition tests (S10, S11, S12, S20.1, S20.2)."""

import json

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from rest_framework.test import APITestCase

from apps.denuncias.models import Denuncia, ModalidadChoices, SeguimientoDenuncia, TipoSituacionChoices

Usuario = get_user_model()


class DenunciaBase(APITestCase):
    def setUp(self):
        self.duenio = Usuario.objects.create_user(
            email="duenio@test.dev",
            password="Usuario123*",
            nombre_completo="Dueña Nombre",
            telefono="3001234567",
            documento="CC-DUENIO",
            role="USUARIO",
        )
        self.otro = Usuario.objects.create_user(documento=documento_unico(), 
            email="otro@test.dev", password="Usuario123*", nombre_completo="Otra", role="USUARIO"
        )
        self.profesional = Usuario.objects.create_user(documento=documento_unico(), 
            email="prof@test.dev", password="Prof123*", nombre_completo="Profesional", role="PROFESIONAL"
        )
        self.admin = Usuario.objects.create_superuser(documento=documento_unico(), 
            email="admin@test.dev", password="Admin123*", nombre_completo="Admin"
        )

    def _crear(self, modalidad):
        self.client.force_authenticate(user=self.duenio)
        return self.client.post(
            "/api/denuncias/mis-denuncias/",
            {
                "modalidad": modalidad,
                "tipo_situacion": TipoSituacionChoices.ACOSO,
                "descripcion": "Descripción ficticia suficientemente larga.",
            },
            format="json",
        )


class DenunciaCreacionTests(DenunciaBase):
    def test_create_anonymous_report(self):
        response = self._crear(ModalidadChoices.ANONIMA)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["denuncia"]["es_anonima"])
        self.assertTrue(
            Denuncia.objects.filter(denunciante=self.duenio).exists()
        )

    def test_create_public_report(self):
        response = self._crear(ModalidadChoices.PUBLICA)
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["denuncia"]["es_anonima"])

    def test_short_description_is_rejected(self):
        self.client.force_authenticate(user=self.duenio)
        response = self.client.post(
            "/api/denuncias/mis-denuncias/",
            {
                "modalidad": ModalidadChoices.PUBLICA,
                "tipo_situacion": TipoSituacionChoices.ACOSO,
                "descripcion": "corta",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("descripcion", response.data)

    def test_missing_required_fields_are_rejected(self):
        self.client.force_authenticate(user=self.duenio)
        response = self.client.post("/api/denuncias/mis-denuncias/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_creation_generates_followup_and_notification(self):
        response = self._crear(ModalidadChoices.PUBLICA)
        denuncia_id = response.data["denuncia"]["id"]
        seguimientos = SeguimientoDenuncia.objects.filter(denuncia_id=denuncia_id)
        # Creation entry + automatic assignment entry (a professional exists).
        self.assertEqual(seguimientos.count(), 2)
        self.assertTrue(
            seguimientos.filter(observacion__startswith="Caso asignado").exists()
        )
        self.client.force_authenticate(user=self.duenio)
        self.assertGreaterEqual(
            self.client.get("/api/notificaciones/no_leidas/").data["no_leidas"], 1
        )


class DenunciaAislamientoTests(DenunciaBase):
    def test_user_cannot_list_other_reports(self):
        self._crear(ModalidadChoices.PUBLICA)
        self.client.force_authenticate(user=self.otro)
        self.assertEqual(self.client.get("/api/denuncias/mis-denuncias/").data["count"], 0)

    def test_user_cannot_retrieve_other_report(self):
        response = self._crear(ModalidadChoices.PUBLICA)
        report_id = response.data["denuncia"]["id"]
        self.client.force_authenticate(user=self.otro)
        self.assertEqual(
            self.client.get(f"/api/denuncias/mis-denuncias/{report_id}/").status_code, 404
        )

    def test_professional_cannot_use_owner_endpoint(self):
        self.client.force_authenticate(user=self.profesional)
        self.assertEqual(self.client.get("/api/denuncias/mis-denuncias/").status_code, 403)

    def test_user_cannot_use_professional_endpoint(self):
        self.client.force_authenticate(user=self.duenio)
        self.assertEqual(self.client.get("/api/denuncias/profesional/").status_code, 403)

    def test_owner_sees_state_changes_in_tracking(self):
        response = self._crear(ModalidadChoices.PUBLICA)
        report_id = response.data["denuncia"]["id"]
        self.client.force_authenticate(user=self.profesional)
        self.client.post(
            f"/api/denuncias/profesional/{report_id}/cambiar_estado/",
            {"estado": "EN_PROCESO", "observacion": "En atención"},
            format="json",
        )
        self.client.force_authenticate(user=self.duenio)
        detalle = self.client.get(f"/api/denuncias/mis-denuncias/{report_id}/").data
        self.assertEqual(detalle["estado"], "EN_PROCESO")
        self.assertEqual(len(detalle["seguimientos"]), 3)


class AnonimatoTests(DenunciaBase):
    """The professional must never receive the reporter identity (S10, S20.2)."""

    IDENTIDAD = ["Dueña Nombre", "duenio@test.dev", "3001234567", "CC-DUENIO"]

    def _payload_profesional(self, modalidad):
        self._crear(modalidad)
        self.client.force_authenticate(user=self.profesional)
        response = self.client.get("/api/denuncias/profesional/")
        self.assertEqual(response.status_code, 200)
        return response

    def test_anonymous_report_hides_identity_from_professional(self):
        response = self._payload_profesional(ModalidadChoices.ANONIMA)
        serialized = json.dumps(response.data, ensure_ascii=False)
        for valor in self.IDENTIDAD:
            self.assertNotIn(valor, serialized, f"Fuga de identidad: {valor}")
        resultado = response.data["results"][0]
        self.assertEqual(resultado["modalidad"], "ANONIMA")
        self.assertTrue(resultado["es_anonima"])
        self.assertIsNone(resultado["solicitante"])

    def test_public_report_shows_operational_contact(self):
        response = self._payload_profesional(ModalidadChoices.PUBLICA)
        resultado = response.data["results"][0]
        self.assertFalse(resultado["es_anonima"])
        self.assertEqual(resultado["solicitante"]["nombre_completo"], "Dueña Nombre")
        self.assertEqual(resultado["solicitante"]["telefono"], "3001234567")

    def test_anonymous_detail_does_not_leak_identity(self):
        self._crear(ModalidadChoices.ANONIMA)
        report_id = Denuncia.objects.get().id
        self.client.force_authenticate(user=self.profesional)
        response = self.client.get(f"/api/denuncias/profesional/{report_id}/")
        serialized = json.dumps(response.data, ensure_ascii=False)
        for valor in self.IDENTIDAD:
            self.assertNotIn(valor, serialized, f"Fuga de identidad: {valor}")

    def test_admin_attention_serializer_also_hides_identity(self):
        self._crear(ModalidadChoices.ANONIMA)
        # Even an administrator using the attention endpoint gets no identity.
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/denuncias/profesional/")
        # Admins are not professionals, so the attention endpoint rejects them.
        self.assertEqual(response.status_code, 403)


class DenunciaEstadoTests(DenunciaBase):
    def test_only_professional_can_change_state(self):
        response = self._crear(ModalidadChoices.PUBLICA)
        report_id = response.data["denuncia"]["id"]
        self.client.force_authenticate(user=self.duenio)
        self.assertEqual(
            self.client.post(
                f"/api/denuncias/profesional/{report_id}/cambiar_estado/",
                {"estado": "FINALIZADA"},
                format="json",
            ).status_code,
            403,
        )

    def test_invalid_state_is_rejected(self):
        response = self._crear(ModalidadChoices.PUBLICA)
        report_id = response.data["denuncia"]["id"]
        self.client.force_authenticate(user=self.profesional)
        self.assertEqual(
            self.client.post(
                f"/api/denuncias/profesional/{report_id}/cambiar_estado/",
                {"estado": "INVENTADO"},
                format="json",
            ).status_code,
            400,
        )

    def test_other_professional_cannot_change_assigned_case(self):
        response = self._crear(ModalidadChoices.PUBLICA)
        report_id = response.data["denuncia"]["id"]
        self.client.force_authenticate(user=self.profesional)
        self.client.post(f"/api/denuncias/profesional/{report_id}/asignarme/")
        otro_prof = Usuario.objects.create_user(documento=documento_unico(), 
            email="prof2@test.dev", password="Prof123*", nombre_completo="Prof 2", role="PROFESIONAL"
        )
        self.client.force_authenticate(user=otro_prof)
        # 404 (not 403): a case assigned to another professional must not even
        # be discoverable through the attention endpoint.
        self.assertEqual(
            self.client.post(
                f"/api/denuncias/profesional/{report_id}/cambiar_estado/",
                {"estado": "FINALIZADA"},
                format="json",
            ).status_code,
            404,
        )


class ProfesionalCasosTests(DenunciaBase):
    """A professional only reaches the cases assigned to them (S4)."""

    def setUp(self):
        super().setUp()
        self.otro_prof = Usuario.objects.create_user(documento=documento_unico(), 
            email="prof2@test.dev",
            password="Prof123*",
            nombre_completo="Prof 2",
            role="PROFESIONAL",
        )

    def _crear_para(self, profesional):
        respuesta = super()._crear(ModalidadChoices.PUBLICA)
        denuncia = Denuncia.objects.get(pk=respuesta.data["denuncia"]["id"])
        denuncia.profesional_asignado = profesional
        denuncia.estado = "EN_PROCESO"
        denuncia.save(update_fields=["profesional_asignado", "estado", "actualizado_en"])
        return denuncia

    def test_list_solo_muestra_los_casos_asignados(self):
        propia = self._crear_para(self.profesional)
        self._crear_para(self.otro_prof)
        self.client.force_authenticate(user=self.profesional)
        respuesta = self.client.get("/api/denuncias/profesional/")
        ids = [denuncia["id"] for denuncia in respuesta.data["results"]]
        self.assertEqual(ids, [propia.id])

    def test_no_muestra_casos_pendientes_de_asignacion(self):
        respuesta = super()._crear(ModalidadChoices.PUBLICA)
        denuncia = Denuncia.objects.get(pk=respuesta.data["denuncia"]["id"])
        denuncia.profesional_asignado = None
        denuncia.save(update_fields=["profesional_asignado"])
        self.client.force_authenticate(user=self.profesional)
        self.assertEqual(self.client.get("/api/denuncias/profesional/").data["count"], 0)

    def test_no_puede_ver_ni_cambiar_casos_ajenos(self):
        ajena = self._crear_para(self.otro_prof)
        self.client.force_authenticate(user=self.profesional)
        self.assertEqual(
            self.client.get(f"/api/denuncias/profesional/{ajena.id}/").status_code, 404
        )
        self.assertEqual(
            self.client.post(
                f"/api/denuncias/profesional/{ajena.id}/cambiar_estado/",
                {"estado": "FINALIZADA"},
                format="json",
            ).status_code,
            404,
        )

    def test_el_endpoint_de_autoasignacion_ya_no_existe(self):
        propia = self._crear_para(self.profesional)
        self.client.force_authenticate(user=self.profesional)
        self.assertEqual(
            self.client.post(f"/api/denuncias/profesional/{propia.id}/asignarme/").status_code,
            404,
        )
