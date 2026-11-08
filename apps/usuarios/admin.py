from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "nombre_completo", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("email", "nombre_completo")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("nombre_completo", "telefono", "documento", "direccion", "fecha_nacimiento")}),
        ("Permisos", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "nombre_completo",
                    "documento",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
