from django.contrib import admin

from .models import Podcast


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    list_display = ("titulo", "publicado", "fecha_publicacion")
    list_filter = ("publicado",)
    search_fields = ("titulo", "descripcion")
