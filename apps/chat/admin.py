"""Chat admin.

Only ``Conversacion`` is registered. ``Mensaje`` is deliberately absent so the
administrator cannot read private chat content from the Django admin either.
"""

from django.contrib import admin

from .models import Conversacion


@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ("id", "denuncia", "actualizado_en")
    filter_horizontal = ("participantes",)
