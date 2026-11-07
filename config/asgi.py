"""ASGI entrypoint wiring HTTP and (authenticated) WebSocket protocols."""

import os
from urllib.parse import parse_qs

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402
from rest_framework_simplejwt.authentication import JWTAuthentication  # noqa: E402

django_asgi_app = get_asgi_application()


class JWTAuthMiddleware:
    """Authenticate WebSocket connections from a `token` query-string value.

    The access token travels in the query string because browsers cannot set
    custom headers on a WebSocket handshake. Invalid or missing tokens leave
    ``scope['user']`` as an anonymous user; consumers still enforce their own
    participant checks before accepting a connection.
    """

    def __init__(self, inner):
        self.inner = inner
        self.authenticator = JWTAuthentication()

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        if token:
            try:
                validated = self.authenticator.get_validated_token(token)
                scope["user"] = self.authenticator.get_user(validated)
            except Exception:  # noqa: BLE001 - malformed/expired token => anonymous
                pass
        return await self.inner(scope, receive, send)


# Imported here so app registry is ready before URLRouter resolves routes.
from apps.chat.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
