"""Chat permissions: participation is the only gate.

The administrator is intentionally NOT granted access, not even when
``is_superuser`` is set: private chats must stay private (HU-06, criterion 7).
"""

from rest_framework.permissions import BasePermission


class EsParticipanteDeConversacion(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        # No superuser/admin bypass on purpose.
        return obj.participantes.filter(pk=user.pk).exists()
