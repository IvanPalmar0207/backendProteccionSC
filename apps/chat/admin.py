"""Chat admin.

Only ``Conversacion`` is registered. ``Mensaje`` is deliberately absent so the
administrator cannot read private chat content from the Django admin either.
Participants are read-only: a Django superuser must not be able to add
itself to a thread and then read it through the API/WebSocket.
"""

from django.contrib import admin

from .models import Conversacion


@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ("id", "denuncia", "actualizado_en")
    readonly_fields = ("participantes",)
