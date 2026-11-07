from django.contrib import admin

from .models import Denuncia, SeguimientoDenuncia


class SeguimientoInline(admin.TabularInline):
    model = SeguimientoDenuncia
    extra = 0
    readonly_fields = ("estado_anterior", "estado_nuevo", "observacion", "autor")


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    """Administrative view kept operational and identity-minimal.

    The reporter identity is intentionally excluded from the list view. The
    attention module (the API) never exposes identity for anonymous reports.
    """

    list_display = ("identificador", "modalidad", "tipo_situacion", "estado", "creado_en")
    list_filter = ("modalidad", "estado", "tipo_situacion")
    search_fields = ("codigo", "descripcion")
    readonly_fields = ("codigo", "creado_en", "actualizado_en")
    inlines = [SeguimientoInline]
