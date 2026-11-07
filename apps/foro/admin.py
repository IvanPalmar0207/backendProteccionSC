from django.contrib import admin

from .models import Publicacion, Respuesta


class RespuestaInline(admin.TabularInline):
    model = Respuesta
    extra = 0


@admin.register(Publicacion)
class PublicacionAdmin(admin.ModelAdmin):
    list_display = ("titulo", "autor", "creado_en")
    search_fields = ("titulo", "contenido")
    inlines = [RespuestaInline]
