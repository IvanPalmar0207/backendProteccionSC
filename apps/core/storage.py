"""Database-backed media storage.

Stores uploaded files as rows in the database so they survive container
redeploys without a Railway volume or an external object-storage account.
Enabled with ``MEDIA_STORAGE=db`` (see ``config/settings.py``).

Files are served through ``apps.core.views.servir_media``.
"""

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseStorage(Storage):
    def _save(self, name, content):
        from .models import StoredFile

        content.seek(0)
        datos = content.read()
        content_type = getattr(content, "content_type", "") or ""
        StoredFile.objects.update_or_create(
            name=name,
            defaults={
                "content": datos,
                "content_type": content_type,
                "size": len(datos),
            },
        )
        return name

    def _open(self, name, mode="rb"):
        from .models import StoredFile

        archivo = StoredFile.objects.filter(name=name).first()
        if archivo is None:
            raise FileNotFoundError(name)
        return ContentFile(bytes(archivo.content), name=name)

    def exists(self, name):
        from .models import StoredFile

        return StoredFile.objects.filter(name=name).exists()

    def delete(self, name):
        from .models import StoredFile

        StoredFile.objects.filter(name=name).delete()

    def size(self, name):
        from .models import StoredFile

        return (
            StoredFile.objects.filter(name=name)
            .values_list("size", flat=True)
            .first()
        )

    def url(self, name):
        return f"{settings.MEDIA_URL}{name}"

    def get_available_name(self, name, max_length=None):
        return name
