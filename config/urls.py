"""Root URL configuration."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from apps.core.views import servir_media

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

# Uploaded media (e.g. news covers). Served by Django: from the database when
# MEDIA_STORAGE=db, otherwise from the local filesystem.
if settings.STORAGES["default"]["BACKEND"].endswith("DatabaseStorage"):
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", servir_media)]
else:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
