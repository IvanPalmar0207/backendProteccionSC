"""End-to-end flow and security audit (Fase 6).

Exercises the real API flows across the three roles and tries to break the
critical privacy rules with direct (manipulated) requests.
"""

import json
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from apps.core.tests.factories import imagen_png
from apps.denuncias.models import Denuncia, EstadoChoices, ModalidadChoices, TipoSituacionChoices

Usuario = get_user_model()


class BaseFlujos(APITestCase):
    def setUp(self):
        self.duenio = Usuario.objects.create_user(
            email="denunciante@test.dev",
            password="Sendero#Calido2026",
            nombre_completo="Valentina Denunciante",
            telefono="3001112233",
            documento="CC-SECRETO",
            role="USUARIO",
        )
        self.otro = Usuario.objects.create_user(
            email="otro@test.dev", password="Sendero#Calido2026",
            nombre_completo="Otra Persona", role="USUARIO",
        )
        self.profesional = Usuario.objects.create_user(
            email="prof@test.dev", password="Brujula#Serena2026",
            nombre_completo="Dra. Profesional", role="PROFESIONAL",
        )
        self.admin = Usuario.objects.create_superuser(
            email="admin@test.dev", password="Faro#Seguro2026", nombre_completo="Admin"
        )

    def como(self, usuario) -> APIClient:
        cliente = APIClient()
        cliente.force_authenticate(user=usuario)
        return cliente

    def crear_denuncia(self, modalidad) -> dict:
        respuesta = self.como(self.duenio).post(
            "/api/denuncias/mis-denuncias/",
            {
                "modalidad": modalidad,
                "tipo_situacion": TipoSituacionChoices.ACOSO,
                "descripcion": "Relato ficticio de prueba funcional suficientemente largo.",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        return respuesta.data["denuncia"]

    IDENTIDAD = ["Valentina Denunciante", "denunciante@test.dev", "3001112233", "CC-SECRETO"]


class FlujoA_DenunciaAnonima(BaseFlujos):
    def test_flujo_completo_anonimo_sin_filtracion(self):
        # 1-3. login + perfil
        login = APIClient().post(
            "/api/auth/login/",
            {"email": "denunciante@test.dev", "password": "Sendero#Calido2026"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["user"]["role"], "USUARIO")
        cliente = APIClient()
        cliente.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["access"])
        self.assertEqual(cliente.get("/api/perfiles/mi-perfil/").status_code, 200)

        # 4-6. denuncia anónima + consulta propia
        creada = cliente.post(
            "/api/denuncias/mis-denuncias/",
            {
                "modalidad": ModalidadChoices.ANONIMA,
                "tipo_situacion": TipoSituacionChoices.ABUSO,
                "descripcion": "Hechos ficticios para verificar el flujo anónimo completo.",
            },
            format="json",
        )
        self.assertEqual(creada.status_code, 201)
        denuncia_id = creada.data["denuncia"]["id"]
        self.assertTrue(creada.data["denuncia"]["es_anonima"])
        self.assertTrue(Denuncia.objects.filter(id=denuncia_id, denunciante=self.duenio).exists())

        # 7-8. el profesional ve el caso, la modalidad, pero no la identidad
        prof = self.como(self.profesional)
        detalle = prof.get(f"/api/denuncias/profesional/{denuncia_id}/")
        self.assertEqual(detalle.status_code, 200)
        self.assertTrue(detalle.data["es_anonima"])
        self.assertIsNone(detalle.data["solicitante"])
        self.assertNotIn(
            "Valentina Denunciante", json.dumps(detalle.data, ensure_ascii=False)
        )

        # 9-10. asignación, cambio de estado y sincronización con el usuario
        self.assertEqual(prof.post(f"/api/denuncias/profesional/{denuncia_id}/asignarme/").status_code, 200)
        cambio = prof.post(
            f"/api/denuncias/profesional/{denuncia_id}/cambiar_estado/",
            {"estado": EstadoChoices.EN_PROCESO, "observacion": "En atención"},
            format="json",
        )
        self.assertEqual(cambio.status_code, 200)
        propio = cliente.get(f"/api/denuncias/mis-denuncias/{denuncia_id}/")
        self.assertEqual(propio.data["estado"], EstadoChoices.EN_PROCESO)
        self.assertGreaterEqual(len(propio.data["seguimientos"]), 3)


class FlujoB_DenunciaPublica(BaseFlujos):
    def test_publica_expone_contacto_operativo_y_sincroniza_estado(self):
        creada = self.crear_denuncia(ModalidadChoices.PUBLICA)
        self.assertEqual(creada["modalidad"], "PUBLICA")

        prof = self.como(self.profesional)
        detalle = prof.get(f"/api/denuncias/profesional/{creada['id']}/")
        self.assertFalse(detalle.data["es_anonima"])
        self.assertEqual(detalle.data["solicitante"]["nombre_completo"], "Valentina Denunciante")
        self.assertEqual(detalle.data["solicitante"]["email"], "denunciante@test.dev")

        prof.post(
            f"/api/denuncias/profesional/{creada['id']}/cambiar_estado/",
            {"estado": EstadoChoices.FINALIZADA},
            format="json",
        )
        propio = self.como(self.duenio).get(f"/api/denuncias/mis-denuncias/{creada['id']}/")
        self.assertEqual(propio.data["estado"], EstadoChoices.FINALIZADA)


class FlujoC_Chat(BaseFlujos):
    def setUp(self):
        super().setUp()
        self.denuncia = self.crear_denuncia(ModalidadChoices.PUBLICA)

    def test_conversacion_privada_entre_participantes(self):
        duenio = self.como(self.duenio)
        prof = self.como(self.profesional)

        # The owner opens the thread for the case.
        abrir = duenio.post("/api/chat/conversaciones/", {"denuncia": self.denuncia["id"]}, format="json")
        self.assertIn(abrir.status_code, (200, 201))
        conversacion_id = abrir.data["id"]

        # A non-participant professional cannot read it yet.
        self.assertEqual(prof.get(f"/api/chat/conversaciones/{conversacion_id}/mensajes/").status_code, 403)

        self.assertEqual(
            duenio.post(
                f"/api/chat/conversaciones/{conversacion_id}/mensajes/",
                {"contenido": "Necesito orientación"},
                format="json",
            ).status_code,
            201,
        )

        # The professional joins by opening the case chat, then can read and reply.
        self.assertIn(
            prof.post("/api/chat/conversaciones/", {"denuncia": self.denuncia["id"]}, format="json").status_code,
            (200, 201),
        )
        self.assertGreaterEqual(
            prof.get(f"/api/chat/conversaciones/{conversacion_id}/mensajes/").data["count"], 1
        )
        self.assertEqual(
            prof.post(
                f"/api/chat/conversaciones/{conversacion_id}/mensajes/",
                {"contenido": "Estoy para acompañarte"},
                format="json",
            ).status_code,
            201,
        )
        historial = duenio.get(f"/api/chat/conversaciones/{conversacion_id}/mensajes/").data
        self.assertEqual(historial["count"], 2)

    def test_tercero_y_admin_no_acceden_a_la_conversacion(self):
        duenio = self.como(self.duenio)
        conversacion_id = duenio.post(
            "/api/chat/conversaciones/", {"denuncia": self.denuncia["id"]}, format="json"
        ).data["id"]

        # A third user: cannot see it in the list nor open it.
        otro = self.como(self.otro)
        self.assertEqual(otro.get("/api/chat/conversaciones/").data["count"], 0)
        self.assertEqual(otro.get(f"/api/chat/conversaciones/{conversacion_id}/").status_code, 403)

        # The administrator must not read private chats.
        admin = self.como(self.admin)
        self.assertEqual(admin.get("/api/chat/conversaciones/").data["count"], 0)
        self.assertEqual(admin.get(f"/api/chat/conversaciones/{conversacion_id}/").status_code, 403)
        self.assertEqual(
            admin.get(f"/api/chat/conversaciones/{conversacion_id}/mensajes/").status_code, 403
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FlujoD_Contenidos(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._overridden_settings["MEDIA_ROOT"], ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email="admin@test.dev", password="Faro#Seguro2026", nombre_completo="Admin"
        )
        self.usuario = Usuario.objects.create_user(
            email="user@test.dev", password="Sendero#Calido2026", nombre_completo="User", role="USUARIO"
        )

    def test_noticia_crear_publicar_despublicar(self):
        admin = APIClient()
        admin.force_authenticate(user=self.admin)
        creada = admin.post(
            "/api/noticias/",
            {
                "titulo": "Noticia de flujo",
                "contenido": "Contenido de prueba.",
                "categoria": "PREVENCION",
                "publicado": True,
                "imagen": imagen_png("portada.png"),
            },
            format="multipart",
        )
        self.assertEqual(creada.status_code, 201)
        self.assertTrue(creada.data["imagen"])
        noticia_id = creada.data["id"]

        # Public user sees it while published.
        self.assertEqual(
            APIClient().get(f"/api/noticias/{noticia_id}/").status_code, 200
        )

        # Unpublish: the public detail is no longer reachable.
        self.assertEqual(
            admin.patch(f"/api/noticias/{noticia_id}/", {"publicado": False}, format="json").status_code,
            200,
        )
        self.assertEqual(APIClient().get(f"/api/noticias/{noticia_id}/").status_code, 404)

    def test_podcast_enlace_https_obligatorio(self):
        admin = APIClient()
        admin.force_authenticate(user=self.admin)
        self.assertEqual(
            admin.post(
                "/api/podcasts/",
                {"titulo": "E", "enlace": "http://inseguro.example.com"},
                format="json",
            ).status_code,
            400,
        )
        ok = admin.post(
            "/api/podcasts/",
            {"titulo": "E", "enlace": "https://open.spotify.com/episode/1", "publicado": True},
            format="json",
        )
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(APIClient().get("/api/podcasts/").data["count"], 1)

    def test_foro_moderacion_por_administrador(self):
        self.client.force_authenticate(user=self.usuario)
        publicacion = self.client.post(
            "/api/foro/publicaciones/", {"titulo": "Hilo", "contenido": "Cuerpo"}, format="json"
        ).data

        admin = APIClient()
        admin.force_authenticate(user=self.admin)
        self.assertEqual(
            admin.patch(
                f"/api/foro/publicaciones/{publicacion['id']}/",
                {"titulo": "Moderado"},
                format="json",
            ).status_code,
            200,
        )
        self.assertEqual(
            admin.delete(f"/api/foro/publicaciones/{publicacion['id']}/").status_code, 204
        )


class FlujoE_Permisos(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email="user@test.dev", password="Sendero#Calido2026", nombre_completo="User", role="USUARIO"
        )
        self.profesional = Usuario.objects.create_user(
            email="prof@test.dev", password="Brujula#Serena2026", nombre_completo="Prof", role="PROFESIONAL"
        )
        self.admin = Usuario.objects.create_superuser(
            email="admin@test.dev", password="Faro#Seguro2026", nombre_completo="Admin"
        )

    def _cliente(self, usuario):
        cliente = APIClient()
        cliente.force_authenticate(user=usuario)
        return cliente

    def test_rutas_cruzadas_rechazadas(self):
        usuario, prof, admin = map(self._cliente, (self.usuario, self.profesional, self.admin))
        # Usuario no entra a módulos de otros roles
        self.assertEqual(usuario.get("/api/denuncias/profesional/").status_code, 403)
        self.assertEqual(usuario.get("/api/auth/usuarios/").status_code, 403)
        # Profesional no administra
        self.assertEqual(prof.get("/api/auth/usuarios/").status_code, 403)
        self.assertEqual(prof.get("/api/denuncias/mis-denuncias/").status_code, 403)
        # Administrador no accede a la atención ni a los chats
        self.assertEqual(admin.get("/api/denuncias/profesional/").status_code, 403)
        self.assertEqual(admin.get("/api/chat/conversaciones/").data["count"], 0)

    def test_manipulacion_de_rol_rechazada(self):
        # El registro ignora el rol enviado
        alta = APIClient().post(
            "/api/auth/register/",
            {
                "email": "nuevo@test.dev",
                "nombre_completo": "Nuevo",
                "password": "Sendero#Calido2026",
                "password_confirm": "Sendero#Calido2026",
                "role": "ADMINISTRADOR",
            },
            format="json",
        )
        self.assertEqual(alta.status_code, 201)
        self.assertEqual(Usuario.objects.get(email="nuevo@test.dev").role, "USUARIO")

        # El perfil propio no permite cambiar el rol
        cliente = self._cliente(self.usuario)
        self.assertEqual(
            cliente.patch("/api/perfiles/mi-perfil/", {"role": "ADMINISTRADOR"}, format="json").status_code,
            200,
        )
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.role, "USUARIO")

        # Un usuario normal no puede cambiar su rol por el endpoint de admin
        self.assertEqual(cliente.patch(f"/api/auth/usuarios/{self.usuario.id}/", {"role": "ADMINISTRADOR"}, format="json").status_code, 403)

    def test_aislamiento_y_manipulacion_de_identificadores(self):
        duenio = APIClient()
        duenio.force_authenticate(user=self.usuario)
        denuncia = duenio.post(
            "/api/denuncias/mis-denuncias/",
            {"modalidad": "ANONIMA", "tipo_situacion": "OTRO", "descripcion": "Relato ficticio para aislamiento entre cuentas."},
            format="json",
        ).data["denuncia"]

        otro = Usuario.objects.create_user(
            email="intruso@test.dev", password="Sendero#Calido2026", nombre_completo="Intruso", role="USUARIO"
        )
        cliente_intruso = self._cliente(otro)
        self.assertEqual(cliente_intruso.get("/api/denuncias/mis-denuncias/").data["count"], 0)
        self.assertEqual(
            cliente_intruso.get(f"/api/denuncias/mis-denuncias/{denuncia['id']}/").status_code, 404
        )
