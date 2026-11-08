"""Authenticated WebSocket consumer for real-time chat.

The connection is authenticated by the ASGI ``JWTAuthMiddleware`` (token in the
``?token=`` query string). Participation is re-verified here before accepting,
so a valid token for an unrelated user cannot join a conversation.
"""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model

Usuario = get_user_model()


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversacion_id = self.scope["url_route"]["kwargs"]["conversacion_id"]
        self.grupo = f"chat_{self.conversacion_id}"
        self.usuario = self.scope.get("user")

        if not await self._puede_participar():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "grupo"):
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if not await self._puede_participar():
            await self.close(code=4403)
            return
        if await self._esta_finalizada():
            # Reject the write but keep the socket for consulting history.
            await self.send_json(
                {
                    "tipo": "error",
                    "code": "denuncia_completada",
                    "detail": (
                        "Esta denuncia ha sido completada. Puedes consultar el "
                        "historial, pero ya no es posible enviar mensajes."
                    ),
                }
            )
            return
        contenido = (content.get("contenido") or "").strip()
        if not contenido:
            return
        mensaje = await self._crear_mensaje(contenido)
        await self.channel_layer.group_send(
            self.grupo, {"type": "chat.message", "mensaje": mensaje}
        )

    async def chat_message(self, event):
        # Re-check on delivery: a reassignment revokes the previous professional
        # immediately, not only when the socket was opened.
        if not await self._puede_participar():
            await self.close(code=4403)
            return
        mensaje = event["mensaje"]
        # Recompute anonymity per delivery so a modality change (public ->
        # anonymous) is honored even on an already-open socket.
        datos = await self._datos_denuncia()
        usuario_id = getattr(self.scope.get("user"), "id", None)
        remitente = mensaje.get("remitente") or {}
        # The broadcast payload carries the real name; each connection masks the
        # anonymous reporter before delivering, so the identity never leaves the
        # server for anyone but the reporter themselves.
        if (
            datos.get("es_anonima")
            and remitente.get("id") == datos.get("denunciante_id")
            and usuario_id != datos.get("denunciante_id")
        ):
            mensaje = {
                **mensaje,
                "remitente": {**remitente, "nombre_completo": "Denunciante anónimo"},
            }
        await self.send_json({"tipo": "mensaje", "mensaje": mensaje})

    @database_sync_to_async
    def _datos_denuncia(self) -> dict:
        from .models import Conversacion

        conversacion = (
            Conversacion.objects.select_related("denuncia")
            .filter(pk=self.conversacion_id)
            .first()
        )
        if conversacion is None:
            return {"es_anonima": False, "denunciante_id": None}
        return {
            "es_anonima": conversacion.denuncia.es_anonima,
            "denunciante_id": conversacion.denuncia.denunciante_id,
        }

    @database_sync_to_async
    def _esta_finalizada(self) -> bool:
        from .models import Conversacion

        return Conversacion.objects.filter(
            pk=self.conversacion_id, denuncia__estado="FINALIZADA"
        ).exists()

    @database_sync_to_async
    def _puede_participar(self) -> bool:
        """Only the reporter or the report's *current* assigned professional."""
        from .models import Conversacion

        usuario = self.scope.get("user")
        if not usuario or not getattr(usuario, "is_authenticated", False):
            return False
        conversacion = (
            Conversacion.objects.select_related("denuncia")
            .filter(pk=self.conversacion_id)
            .first()
        )
        if conversacion is None:
            return False
        return conversacion.acceso_permitido(usuario)

    @database_sync_to_async
    def _crear_mensaje(self, contenido: str) -> dict:
        from apps.notificaciones.services import notificar_mensaje

        from .models import Conversacion, Mensaje

        conversacion = Conversacion.objects.get(pk=self.conversacion_id)
        mensaje = Mensaje.objects.create(
            conversacion=conversacion, remitente=self.scope["user"], contenido=contenido
        )
        conversacion.save(update_fields=["actualizado_en"])
        notificar_mensaje(mensaje)
        return {
            "id": mensaje.id,
            "remitente": {
                "id": mensaje.remitente_id,
                "nombre_completo": mensaje.remitente.nombre_completo,
                "role": mensaje.remitente.role,
            },
            "contenido": mensaje.contenido,
            "leido": mensaje.leido,
            "creado_en": mensaje.creado_en.isoformat(),
        }
