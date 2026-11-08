"""Chat permissions: only the reporter or the assigned professional.

Membership in the legacy ``participantes`` M2M is NOT the gate: access is
computed from the report (its author and its *current* assigned professional),
so a reassignment revokes the previous professional immediately. The
administrator is denied even when ``is_superuser`` is set (HU-06).
"""

from rest_framework.permissions import BasePermission


class EsParticipanteDeConversacion(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return obj.acceso_permitido(request.user)
