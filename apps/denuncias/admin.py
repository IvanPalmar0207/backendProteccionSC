from django.contrib import admin

from .models import Denuncia, SeguimientoDenuncia


class SeguimientoInline(admin.TabularInline):
    """Read-only follow-up log.

    ``autor`` is deliberately excluded: for an anonymous report the first entry
    is created by the reporter, so showing the author would leak their identity.
    """

    model = SeguimientoDenuncia
    extra = 0
    can_delete = False
    fields = ("creado_en", "estado_anterior", "estado_nuevo", "observacion")
    readonly_fields = ("creado_en", "estado_anterior", "estado_nuevo", "observacion")


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    """Operational, identity-free administrative view.

    The reporter link (``denunciante``) is excluded from the form so an
    administrator cannot obtain the identity of an anonymous reporter through
    the Django admin either; it stays only in the database and in the owner's
    own API responses. Records are not created here (the API always sets the
    reporter), so ``has_add_permission`` is disabled.
    """

    list_display = ("identificador", "modalidad", "tipo_situacion", "estado", "creado_en")
    list_filter = ("modalidad", "estado", "tipo_situacion")
    search_fields = ("codigo",)
    exclude = ("denunciante",)
    readonly_fields = ("codigo", "creado_en", "actualizado_en")
    inlines = [SeguimientoInline]

    def has_add_permission(self, request):
        return False
