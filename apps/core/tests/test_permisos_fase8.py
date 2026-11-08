"""Cross-role permission matrix (Fase 8, section 7).

One test per scenario of the acceptance table, so the security boundary is
auditable from a single module.
"""

from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from rest_framework.test import APITestCase

from apps.chat.models import Conversacion, Mensaje
from apps.denuncias.models import Denuncia, ModalidadChoices, TipoSituacionChoices
from apps.notificaciones.services import notificar

Usuario = get_user_model()

PERFIL = "/api/perfiles/mi-perfil/"


class PermisosBase(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(documento=documento_unico(), 
            email="mat-usuario@test.dev",
            password="Usuario123*",
            nombre_completo="Usuario Matriz",
            role="USUARIO",
        )
        self.profesional = Usuario.objects.create_user(documento=documento_unico(), 
            email="mat-prof@test.dev",
            password="Prof123*",
            nombre_completo="Profesional Matriz",
            role="PROFESIONAL",
        )
        self.otro_prof = Usuario.objects.create_user(documento=documento_unico(), 
            email="mat-prof2@test.dev",
            password="Prof123*",
            nombre_completo="Profesional Dos",
            role="PROFESIONAL",
        )
        self.admin = Usuario.objects.create_superuser(documento=documento_unico(), 
            email="mat-admin@test.dev", password="Admin123*", nombre_completo="Admin Matriz"
        )
        self.denuncia = Denuncia.objects.create(
            denunciante=self.usuario,
            modalidad=ModalidadChoices.PUBLICA,
            tipo_situacion=TipoSituacionChoices.ACOSO,
            descripcion="Descripción de prueba suficientemente larga.",
            profesional_asignado=self.profesional,
        )
        self.conversacion = Conversacion.objects.create(denuncia=self.denuncia)
        self.conversacion.participantes.add(self.usuario, self.profesional)


class PerfilPermisosTests(PermisosBase):
    def test_1_usuario_consulta_su_perfil(self):
        self.client.force_authenticate(user=self.usuario)
        respuesta = self.client.get(PERFIL)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["email"], self.usuario.email)

    def test_2_usuario_no_puede_modificar_otro_perfil(self):
        self.client.force_authenticate(user=self.usuario)
        # There is no id-based route: the profile always resolves to the caller.
        self.assertIn(self.client.get("/api/perfiles/1/").status_code, (404, 405))
        self.client.patch(
            PERFIL, {"nombre_completo": "Nombre cambiado"}, format="json"
        )
        self.otro_prof.refresh_from_db()
        self.assertEqual(self.otro_prof.nombre_completo, "Profesional Dos")

    def test_3_profesional_consulta_su_perfil(self):
        self.client.force_authenticate(user=self.profesional)
        respuesta = self.client.get(PERFIL)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["email"], self.profesional.email)

    def test_4_profesional_no_puede_modificar_otro_perfil(self):
        self.client.force_authenticate(user=self.profesional)
        respuesta = self.client.patch(PERFIL, {"nombre_completo": "X"}, format="json")
        self.assertEqual(respuesta.status_code, 200)
        # The change applied to the caller only.
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.nombre_completo, "Usuario Matriz")

    def test_7_administrador_consulta_su_perfil(self):
        self.client.force_authenticate(user=self.admin)
        respuesta = self.client.get(PERFIL)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["email"], self.admin.email)

    def test_8_administrador_modifica_su_perfil(self):
        self.client.force_authenticate(user=self.admin)
        respuesta = self.client.patch(PERFIL, {"telefono": "3000000000"}, format="json")
        self.assertEqual(respuesta.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.telefono, "3000000000")
        # The role can never be changed through the profile endpoint.
        self.client.patch(PERFIL, {"role": "USUARIO"}, format="json")
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, "ADMINISTRADOR")


class DenunciaProfesionalPermisosTests(PermisosBase):
    def test_5_profesional_consulta_sus_casos_asignados(self):
        self.client.force_authenticate(user=self.profesional)
        respuesta = self.client.get(f"/api/denuncias/profesional/{self.denuncia.id}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["id"], self.denuncia.id)

    def test_6_profesional_no_consulta_casos_ajenos(self):
        self.client.force_authenticate(user=self.otro_prof)
        self.assertEqual(
            self.client.get("/api/denuncias/profesional/").data["count"], 0
        )
        self.assertEqual(
            self.client.get(f"/api/denuncias/profesional/{self.denuncia.id}/").status_code,
            404,
        )


class ChatAdministradorPermisosTests(PermisosBase):
    def test_9_administrador_no_accede_al_chat(self):
        self.client.force_authenticate(user=self.admin)
        # Listing never includes a conversation the admin is not part of.
        self.assertEqual(self.client.get("/api/chat/conversaciones/").data["count"], 0)
        self.assertEqual(
            self.client.get(f"/api/chat/conversaciones/{self.conversacion.id}/").status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/"
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/chat/conversaciones/{self.conversacion.id}/mensajes/",
                {"contenido": "intruso"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                "/api/chat/conversaciones/", {"denuncia": self.denuncia.id}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(Mensaje.objects.count(), 0)


class NotificacionPermisosTests(PermisosBase):
    def test_10_usuario_consulta_sus_notificaciones(self):
        notificar(self.usuario, "Propia")
        self.client.force_authenticate(user=self.usuario)
        respuesta = self.client.get("/api/notificaciones/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["count"], 1)

    def test_11_profesional_consulta_sus_notificaciones(self):
        notificar(self.profesional, "Para el profesional")
        self.client.force_authenticate(user=self.profesional)
        respuesta = self.client.get("/api/notificaciones/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["count"], 1)
        self.assertEqual(respuesta.data["results"][0]["titulo"], "Para el profesional")

    def test_12_usuario_no_consulta_notificaciones_ajenas(self):
        ajena = notificar(self.profesional, "Privada del profesional")
        self.client.force_authenticate(user=self.usuario)
        self.assertEqual(self.client.get("/api/notificaciones/").data["count"], 0)
        self.assertEqual(
            self.client.get(f"/api/notificaciones/{ajena.id}/").status_code, 404
        )

    def test_13_profesional_no_consulta_notificaciones_ajenas(self):
        ajena = notificar(self.usuario, "Privada del usuario")
        self.client.force_authenticate(user=self.profesional)
        self.assertEqual(self.client.get("/api/notificaciones/").data["count"], 0)
        self.assertEqual(
            self.client.get(f"/api/notificaciones/{ajena.id}/").status_code, 404
        )
