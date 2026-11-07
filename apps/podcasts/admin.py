from django.contrib import admin

from .models import Podcast


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    list_display = ("titulo", "programa", "plataforma", "publicado", "fecha_publicacion")
    list_filter = ("plataforma", "publicado")
    search_fields = ("titulo", "programa", "descripcion")
