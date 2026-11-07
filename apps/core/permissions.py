"""Shared, reusable permissions based on the platform roles."""


class RolePermission:
    """Mixin factory helpers to keep role checks in one place."""

    role = None

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or getattr(user, "role", None) == self.role)
        )


class IsUsuario(RolePermission):
    role = "USUARIO"


class IsProfesional(RolePermission):
    role = "PROFESIONAL"


class IsAdministrador(RolePermission):
    role = "ADMINISTRADOR"


class IsOwnerOrReadOnly:
    """Object-level permission: only the object owner may modify it."""

    owner_field = "usuario"

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        owner = getattr(obj, self.owner_field, None)
        if owner is None:
            owner = getattr(obj, "denunciante", None)
        return owner == request.user
