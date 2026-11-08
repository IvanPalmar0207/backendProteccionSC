"""Core views: serve database-stored media."""

from django.http import Http404, HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def servir_media(request, path):
    """Serve a file stored by ``DatabaseStorage`` (MEDIA_STORAGE=db)."""
    from .models import StoredFile

    archivo = StoredFile.objects.filter(name=path).first()
    if archivo is None:
        raise Http404("Archivo no encontrado")
    respuesta = HttpResponse(
        bytes(archivo.content),
        content_type=archivo.content_type or "application/octet-stream",
    )
    respuesta["Content-Length"] = str(archivo.size)
    return respuesta
