"""WebSocket chat tests (HU-06 criterion 8, S13).

The consumer is tested against a dedicated ASGI application that composes the
real ``JWTAuthMiddleware`` with the chat ``URLRouter`` but omits
``AllowedHostsOriginValidator``. Origin validation depends on ``ALLOWED_HOSTS``
and makes the test environment flaky; participation and JWT handling — the
behavior under test — are identical.
"""

from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from apps.core.tests.factories import documento_unico
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chat.models import Conversacion
from apps.chat.routing import websocket_urlpatterns
from apps.denuncias.models import Denuncia, ModalidadChoices, TipoSituacionChoices
from config.asgi import JWTAuthMiddleware

Usuario = get_user_model()

# Test-only application: same auth + routing, no origin validator.
test_application = JWTAuthMiddleware(URLRouter(websocket_urlpatterns))


class ChatWebSocketTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.duenio = Usuario.objects.create_user(documento=documento_unico(), 
            email="ws-duenio@test.dev", password="Usuario123*", nombre_completo="Dueña WS", role="USUARIO"
        )
        self.profesional = Usuario.objects.create_user(documento=documento_unico(), 
            email="ws-prof@test.dev", password="Prof123*", nombre_completo="Profesional WS", role="PROFESIONAL"
        )
        self.intruso = Usuario.objects.create_user(documento=documento_unico(), 
            email="ws-intruso@test.dev", password="Usuario123*", nombre_completo="Intruso", role="USUARIO"
        )
        self.profesional2 = Usuario.objects.create_user(documento=documento_unico(), 
            email="ws-prof2@test.dev", password="Prof123*", nombre_completo="Profesional Dos WS", role="PROFESIONAL"
        )
        self.denuncia = Denuncia.objects.create(
            denunciante=self.duenio,
            modalidad=ModalidadChoices.ANONIMA,
            tipo_situacion=TipoSituacionChoices.ACOSO,
            descripcion="Descripción de prueba suficientemente larga.",
            profesional_asignado=self.profesional,
        )
        self.conversacion = Conversacion.objects.create(denuncia=self.denuncia)
        self.conversacion.participantes.add(self.duenio, self.profesional)

        # Build tokens in this synchronous setup: with the token blacklist app
        # enabled, RefreshToken.for_user writes to the database and cannot run
        # inside the async test body.
        self.token_duenio = str(RefreshToken.for_user(self.duenio).access_token)
        self.token_profesional = str(RefreshToken.for_user(self.profesional).access_token)
        self.token_intruso = str(RefreshToken.for_user(self.intruso).access_token)
        self.token_profesional2 = str(RefreshToken.for_user(self.profesional2).access_token)

    def test_participants_exchange_message_in_real_time(self):
        async_to_sync(self._run_exchange)()

    async def _run_exchange(self):
        url = f"/ws/chat/{self.conversacion.id}/"
        consumidor_a = WebsocketCommunicator(
            test_application, url + f"?token={self.token_duenio}"
        )
        consumidor_b = WebsocketCommunicator(
            test_application, url + f"?token={self.token_profesional}"
        )
        conectado_a, _ = await consumidor_a.connect()
        conectado_b, _ = await consumidor_b.connect()
        self.assertTrue(conectado_a)
        self.assertTrue(conectado_b)

        await consumidor_a.send_json_to({"contenido": "Mensaje en tiempo real"})
        recibido = await consumidor_b.receive_json_from(timeout=5)
        self.assertEqual(recibido["tipo"], "mensaje")
        self.assertEqual(recibido["mensaje"]["contenido"], "Mensaje en tiempo real")
        # The report is anonymous: the professional receives a masked name.
        self.assertEqual(
            recibido["mensaje"]["remitente"]["nombre_completo"], "Denunciante anónimo"
        )
        # The reporter still sees their own name in their own echo.
        propio = await consumidor_a.receive_json_from(timeout=5)
        self.assertEqual(propio["mensaje"]["remitente"]["nombre_completo"], "Dueña WS")

        await consumidor_a.disconnect()
        await consumidor_b.disconnect()

    def test_non_participant_is_rejected(self):
        async_to_sync(self._run_rejection)()

    async def _run_rejection(self):
        url = f"/ws/chat/{self.conversacion.id}/?token={self.token_intruso}"
        comunicador = WebsocketCommunicator(test_application, url)
        conectado, _ = await comunicador.connect()
        self.assertFalse(conectado)

    def test_unassigned_professional_is_rejected(self):
        async_to_sync(self._run_unassigned_rejection)()

    async def _run_unassigned_rejection(self):
        # A case without an assigned professional must reject the socket.
        self.denuncia.profesional_asignado = None
        await self.denuncia.asave(update_fields=["profesional_asignado"])
        url = f"/ws/chat/{self.conversacion.id}/?token={self.token_profesional}"
        comunicador = WebsocketCommunicator(test_application, url)
        conectado, _ = await comunicador.connect()
        self.assertFalse(conectado)

    def test_reassignment_revokes_the_previous_professional(self):
        async_to_sync(self._run_reassignment)()

    async def _run_reassignment(self):
        url = f"/ws/chat/{self.conversacion.id}/?token={self.token_profesional}"
        comunicador = WebsocketCommunicator(test_application, url)
        conectado, _ = await comunicador.connect()
        self.assertTrue(conectado)

        # Reassign the case to another professional while the socket is open.
        self.denuncia.profesional_asignado = self.profesional2
        await self.denuncia.asave(update_fields=["profesional_asignado"])

        # The old connection is no longer authorized to send.
        await comunicador.send_json_to({"contenido": "sigo aquí"})
        with self.assertRaises(Exception):
            await comunicador.receive_json_from(timeout=2)
        await comunicador.disconnect()

    def test_anonymity_is_recomputed_after_modality_change(self):
        async_to_sync(self._run_modality_change)()

    async def _run_modality_change(self):
        # Start as a public report, then turn it anonymous while sockets are open.
        self.denuncia.modalidad = "PUBLICA"
        await self.denuncia.asave(update_fields=["modalidad"])
        url = f"/ws/chat/{self.conversacion.id}/"
        duenio = WebsocketCommunicator(test_application, url + f"?token={self.token_duenio}")
        prof = WebsocketCommunicator(test_application, url + f"?token={self.token_profesional}")
        self.assertTrue((await duenio.connect())[0])
        self.assertTrue((await prof.connect())[0])

        self.denuncia.modalidad = "ANONIMA"
        await self.denuncia.asave(update_fields=["modalidad"])
        await duenio.send_json_to({"contenido": "ahora anónimo"})
        recibido = await prof.receive_json_from(timeout=5)
        self.assertEqual(
            recibido["mensaje"]["remitente"]["nombre_completo"], "Denunciante anónimo"
        )
        await duenio.disconnect()
        await prof.disconnect()

    def test_finished_report_rejects_socket_writes(self):
        async_to_sync(self._run_finished)()

    async def _run_finished(self):
        from apps.chat.models import Mensaje

        # Finish the report after the socket is open.
        self.denuncia.estado = "FINALIZADA"
        await self.denuncia.asave(update_fields=["estado"])
        url = f"/ws/chat/{self.conversacion.id}/?token={self.token_profesional}"
        comunicador = WebsocketCommunicator(test_application, url)
        conectado, _ = await comunicador.connect()
        self.assertTrue(conectado)

        await comunicador.send_json_to({"contenido": "no permitido"})
        respuesta = await comunicador.receive_json_from(timeout=5)
        self.assertEqual(respuesta["tipo"], "error")
        self.assertEqual(respuesta["code"], "denuncia_completada")
        self.assertFalse(await Mensaje.objects.filter(contenido="no permitido").aexists())
        await comunicador.disconnect()

    def test_message_is_persisted_after_socket_write(self):
        async_to_sync(self._run_persistence)()

    async def _run_persistence(self):
        from apps.chat.models import Mensaje

        url = f"/ws/chat/{self.conversacion.id}/?token={self.token_duenio}"
        comunicador = WebsocketCommunicator(test_application, url)
        await comunicador.connect()
        await comunicador.send_json_to({"contenido": "Persistime"})
        await comunicador.receive_json_from(timeout=5)
        await comunicador.disconnect()
        self.assertTrue(
            await Mensaje.objects.filter(contenido="Persistime").aexists()
        )
