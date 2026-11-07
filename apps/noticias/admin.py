from django.contrib import admin

from .models import Noticia


@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "destacada", "publicado", "fecha_publicacion")
    list_filter = ("categoria", "destacada", "publicado")
    search_fields = ("titulo", "contenido")
