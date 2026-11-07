"""Profile consultation and update for the authenticated account."""

from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from .serializers import PerfilSerializer


class MiPerfilView(RetrieveUpdateAPIView):
    """GET/PUT/PATCH the caller's own profile."""

    serializer_class = PerfilSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
