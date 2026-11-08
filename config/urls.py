"""Root URL configuration."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.usuarios.urls")),
    path("api/perfiles/", include("apps.perfiles.urls")),
    path("api/denuncias/", include("apps.denuncias.urls")),
    path("api/chat/", include("apps.chat.urls")),
    path("api/noticias/", include("apps.noticias.urls")),
    path("api/podcasts/", include("apps.podcasts.urls")),
    path("api/foro/", include("apps.foro.urls")),
    path("api/notificaciones/", include("apps.notificaciones.urls")),
]

# Uploaded media (e.g. news covers). Served by Django so it works both in
# development and in production behind the persistent volume (MEDIA_ROOT).
# For high traffic, put object storage/CDN in front of it.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
