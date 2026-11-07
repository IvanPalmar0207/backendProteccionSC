"""Shared, reusable permissions based on the platform roles."""

from rest_framework.permissions import BasePermission


class RolePermission(BasePermission):
    """Base class: allow only authenticated users with a matching role.

    Subclasses ``BasePermission`` so DRF object-level checks work too: role is
    a view-level decision, so object checks inherit the same role test.
    """

    role = None

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or getattr(user, "role", None) == self.role)
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsUsuario(RolePermission):
    role = "USUARIO"


class IsProfesional(RolePermission):
    role = "PROFESIONAL"


class IsAdministrador(RolePermission):
    role = "ADMINISTRADOR"


class IsOwnerOrReadOnly(BasePermission):
    """Object-level permission: only the object owner may modify it."""

    owner_field = "usuario"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        owner = getattr(obj, self.owner_field, None)
        if owner is None:
            owner = getattr(obj, "denunciante", None)
        return owner == request.user
