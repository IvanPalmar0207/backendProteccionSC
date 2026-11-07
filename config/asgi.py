"""ASGI entrypoint wiring HTTP and (authenticated) WebSocket protocols."""

import os
from urllib.parse import parse_qs

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from channels.db import database_sync_to_async  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402
from rest_framework_simplejwt.authentication import JWTAuthentication  # noqa: E402

django_asgi_app = get_asgi_application()


class JWTAuthMiddleware:
    """Authenticate WebSocket connections from a `token` query-string value.

    The access token travels in the query string because browsers cannot set
    custom headers on a WebSocket handshake. Database work runs through
    ``database_sync_to_async``: touching the ORM synchronously inside an async
    ASGI call raises ``SynchronousOnlyOperation``. Invalid or missing tokens
    leave ``scope['user']`` as an anonymous user; consumers still enforce their
    own participant checks before accepting a connection.
    """

    def __init__(self, inner):
        self.inner = inner

    @database_sync_to_async
    def _authenticate(self, token):
        try:
            authenticator = JWTAuthentication()
            validated = authenticator.get_validated_token(token)
            return authenticator.get_user(validated)
        except Exception:  # noqa: BLE001 - malformed/expired token => anonymous
            return None

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        if token:
            user = await self._authenticate(token)
            if user is not None:
                scope["user"] = user
        return await self.inner(scope, receive, send)


# Imported here so the app registry is ready before URLRouter resolves routes.
from apps.chat.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
