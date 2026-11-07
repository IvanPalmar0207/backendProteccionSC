from django.contrib import admin

from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "titulo", "tipo", "leida", "creado_en")
    list_filter = ("tipo", "leida")
    search_fields = ("usuario__email", "titulo")
