"""Root URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
