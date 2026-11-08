"""Automatic assignment, strict professional table and admin assignment (Fase 11)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.tests.factories import documento_unico
from apps.denuncias.models import Denuncia, EstadoChoices

Usuario = get_user_model()
CREAR = "/api/denuncias/mis-denuncias/"
PROF = "/api/denuncias/profesional/"
ADMIN = "/api/denuncias/admin/"


def crear_profesional(email: str, activo: bool = True):
    return Usuario.objects.create_user(
        email=email,
        password="Prof123*",
        nombre_completo=email.split("@")[0],
        documento=documento_unico(),
        role="PROFESIONAL",
        is_active=activo,
    )


class AsignacionBase(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email="asi-usuario@test.dev",
            password="Usuario123*",
            nombre_completo="Usuario Asignación",
            documento=documento_unico(),
            role="USUARIO",
        )
        self.client.force_authenticate(user=self.usuario)

    def _crear(self):
        return self.client.post(
            CREAR,
            {
                "modalidad": "PUBLICA",
                "tipo_situacion": "ACOSO",
                "descripcion": "Descripción de prueba suficientemente larga.",
            },
            format="json",
        )

    def _denuncia_directa(self, profesional=None, estado=EstadoChoices.PENDIENTE):
        return Denuncia.objects.create(
            denunciante=self.usuario,
            modalidad="PUBLICA",
            tipo_situacion="ACOSO",
            descripcion="Descripción de prueba suficientemente larga.",
            profesional_asignado=profesional,
            estado=estado,
        )


class AsignacionAutomaticaTests(AsignacionBase):
    def test_asigna_automaticamente_al_profesional_disponible(self):
        profesional = crear_profesional("prof-auto@test.dev")
        response = self._crear()
        self.assertEqual(response.status_code, 201)
        denuncia = Denuncia.objects.get(pk=response.data["denuncia"]["id"])
        self.assertEqual(denuncia.profesional_asignado_id, profesional.id)
        self.assertEqual(denuncia.estado, EstadoChoices.EN_PROCESO)

    def test_elige_al_de_menos_casos_activos(self):
        p1 = crear_profesional("prof-uno@test.dev")
        p2 = crear_profesional("prof-dos@test.dev")
        # p1 already has an active case; p2 has none.
        self._denuncia_directa(profesional=p1, estado=EstadoChoices.EN_PROCESO)
        response = self._crear()
        denuncia = Denuncia.objects.get(pk=response.data["denuncia"]["id"])
        self.assertEqual(denuncia.profesional_asignado_id, p2.id)

    def test_desempate_por_id(self):
        p1 = crear_profesional("prof-a@test.dev")
        crear_profesional("prof-b@test.dev")
        response = self._crear()
        denuncia = Denuncia.objects.get(pk=response.data["denuncia"]["id"])
        self.assertEqual(denuncia.profesional_asignado_id, p1.id)

    def test_no_asigna_inactivos_ni_administradores(self):
        crear_profesional("prof-inactivo@test.dev", activo=False)
        Usuario.objects.create_superuser(
            email="admin@test.dev",
            password="Admin123*",
            nombre_completo="Admin",
            documento=documento_unico(),
        )
        response = self._crear()
        denuncia = Denuncia.objects.get(pk=response.data["denuncia"]["id"])
        self.assertIsNone(denuncia.profesional_asignado_id)
        self.assertEqual(denuncia.estado, EstadoChoices.PENDIENTE)

    def test_sin_profesionales_queda_pendiente(self):
        response = self._crear()
        self.assertEqual(response.status_code, 201)
        denuncia = Denuncia.objects.get(pk=response.data["denuncia"]["id"])
        self.assertIsNone(denuncia.profesional_asignado_id)
        ultimo = denuncia.seguimientos.order_by("creado_en").last()
        self.assertIn("Pendiente de asignación", ultimo.observacion)

    def test_registra_el_seguimiento_de_la_asignacion(self):
        profesional = crear_profesional("prof-seg@test.dev")
        response = self._crear()
        denuncia = Denuncia.objects.get(pk=response.data["denuncia"]["id"])
        asignacion = denuncia.seguimientos.filter(observacion__startswith="Caso asignado").first()
        self.assertIsNotNone(asignacion)
        self.assertIsNone(asignacion.autor_id)
        self.assertIn(profesional.nombre_completo, asignacion.observacion)


class ProfesionalTablaEstrictaTests(AsignacionBase):
    def setUp(self):
        super().setUp()
        self.p1 = crear_profesional("tab-uno@test.dev")
        self.p2 = crear_profesional("tab-dos@test.dev")
        self.d1 = self._denuncia_directa(profesional=self.p1, estado=EstadoChoices.EN_PROCESO)
        self.d2 = self._denuncia_directa(profesional=self.p2, estado=EstadoChoices.EN_PROCESO)

    def test_profesional_solo_ve_sus_casos(self):
        self.client.force_authenticate(user=self.p1)
        response = self.client.get(PROF)
        ids = [d["id"] for d in response.data["results"]]
        self.assertEqual(ids, [self.d1.id])
        self.assertNotIn(self.d2.id, ids)

    def test_no_ve_casos_pendientes_de_asignacion(self):
        self._denuncia_directa(profesional=None)
        self.client.force_authenticate(user=self.p1)
        response = self.client.get(PROF)
        ids = [d["id"] for d in response.data["results"]]
        self.assertEqual(ids, [self.d1.id])

    def test_no_puede_ver_el_detalle_ajeno(self):
        self.client.force_authenticate(user=self.p2)
        self.assertEqual(self.client.get(f"{PROF}{self.d1.id}/").status_code, 404)

    def test_no_puede_cambiar_estado_ajeno(self):
        self.client.force_authenticate(user=self.p2)
        response = self.client.post(
            f"{PROF}{self.d1.id}/cambiar_estado/", {"estado": "FINALIZADA"}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_los_filtros_solo_operan_sobre_sus_casos(self):
        self.client.force_authenticate(user=self.p1)
        response = self.client.get(PROF, {"estado": "EN_PROCESO"})
        ids = [d["id"] for d in response.data["results"]]
        self.assertEqual(ids, [self.d1.id])

    def test_el_endpoint_de_autoasignacion_ya_no_existe(self):
        self.client.force_authenticate(user=self.p1)
        response = self.client.post(f"{PROF}{self.d2.id}/asignarme/")
        self.assertEqual(response.status_code, 404)


class AdminAsignacionTests(AsignacionBase):
    def setUp(self):
        super().setUp()
        self.admin = Usuario.objects.create_superuser(
            email="asi-admin@test.dev",
            password="Admin123*",
            nombre_completo="Admin Asignación",
            documento=documento_unico(),
        )
        self.p1 = crear_profesional("adm-uno@test.dev")
        self.p2 = crear_profesional("adm-dos@test.dev")

    def test_usuario_no_accede_al_endpoint_admin(self):
        self.assertEqual(self.client.get(ADMIN).status_code, 403)

    def test_admin_asigna_un_caso_pendiente(self):
        denuncia = self._denuncia_directa(profesional=None)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{ADMIN}{denuncia.id}/asignar/", {"profesional": self.p1.id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        denuncia.refresh_from_db()
        self.assertEqual(denuncia.profesional_asignado_id, self.p1.id)
        self.assertEqual(denuncia.estado, EstadoChoices.EN_PROCESO)

    def test_admin_reasigna_y_registra_el_cambio(self):
        denuncia = self._denuncia_directa(profesional=self.p1, estado=EstadoChoices.EN_PROCESO)
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"{ADMIN}{denuncia.id}/asignar/", {"profesional": self.p2.id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        denuncia.refresh_from_db()
        self.assertEqual(denuncia.profesional_asignado_id, self.p2.id)
        ultimo = denuncia.seguimientos.order_by("creado_en").last()
        self.assertEqual(ultimo.autor_id, self.admin.id)
        self.assertIn("Reasignado", ultimo.observacion)

    def test_admin_no_asigna_usuarios_ni_inactivos(self):
        denuncia = self._denuncia_directa(profesional=None)
        inactivo = crear_profesional("adm-inactivo@test.dev", activo=False)
        self.client.force_authenticate(user=self.admin)
        for candidato in (self.usuario.id, inactivo.id, 999999):
            response = self.client.post(
                f"{ADMIN}{denuncia.id}/asignar/", {"profesional": candidato}, format="json"
            )
            self.assertEqual(response.status_code, 400)

    def test_admin_lista_profesionales_habilitados(self):
        crear_profesional("adm-inactivo2@test.dev", activo=False)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"{ADMIN}profesionales/")
        ids = [p["id"] for p in response.data]
        self.assertIn(self.p1.id, ids)
        self.assertIn(self.p2.id, ids)

    def test_admin_puede_filtrar_pendientes(self):
        pendiente = self._denuncia_directa(profesional=None)
        self._denuncia_directa(profesional=self.p1, estado=EstadoChoices.EN_PROCESO)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(ADMIN, {"asignacion": "pendientes"})
        ids = [d["id"] for d in response.data["results"]]
        self.assertEqual(ids, [pendiente.id])
