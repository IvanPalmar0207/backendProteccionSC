"""Demo data tests (F2-S15, F2-S16)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.denuncias.models import Denuncia, ModalidadChoices
from apps.noticias.models import Noticia
from apps.podcasts.models import Podcast

Usuario = get_user_model()

DEMO = [
    ("usuario@proteccioninmediata.test", "Sendero#Calido2026", "USUARIO"),
    ("profesional@proteccioninmediata.test", "Brujula#Serena2026", "PROFESIONAL"),
    ("admin@proteccioninmediata.test", "Faro#Seguro2026", "ADMINISTRADOR"),
]


class SeedDemoTests(APITestCase):
    def _sembrar(self):
        call_command("seed_demo", verbosity=0)

    def test_seed_is_idempotent(self):
        self._sembrar()
        conteo = (
            Usuario.objects.count(),
            Noticia.objects.count(),
            Podcast.objects.count(),
            Denuncia.objects.filter(descripcion__startswith="[demo]").count(),
        )
        self._sembrar()
        self.assertEqual(
            conteo,
            (
                Usuario.objects.count(),
                Noticia.objects.count(),
                Podcast.objects.count(),
                Denuncia.objects.filter(descripcion__startswith="[demo]").count(),
            ),
        )

    def test_demo_accounts_exist_with_roles_and_compliant_passwords(self):
        self._sembrar()
        for email, password, role in DEMO:
            usuario = Usuario.objects.get(email=email)
            self.assertEqual(usuario.role, role)
            self.assertTrue(usuario.is_active)
            # Same rule as registration: validate with the account as context.
            validate_password(password, user=usuario)

    def test_demo_accounts_authenticate_through_the_normal_flow(self):
        self._sembrar()
        for email, password, role in DEMO:
            respuesta = self.client.post(
                "/api/auth/login/", {"email": email, "password": password}, format="json"
            )
            self.assertEqual(respuesta.status_code, 200, email)
            self.assertEqual(respuesta.data["user"]["role"], role)
            self.assertIn("access", respuesta.data)

    def test_demo_content_matches_the_new_rules(self):
        self._sembrar()
        self.assertEqual(
            Denuncia.objects.filter(
                descripcion__startswith="[demo]", modalidad=ModalidadChoices.ANONIMA
            ).count(),
            1,
        )
        self.assertEqual(
            Denuncia.objects.filter(
                descripcion__startswith="[demo]", modalidad=ModalidadChoices.PUBLICA
            ).count(),
            1,
        )
        self.assertTrue(Noticia.objects.filter(destacada=True).exists())
        self.assertFalse(Noticia.objects.filter(categoria="").exists())
        for podcast in Podcast.objects.all():
            self.assertTrue(podcast.enlace.startswith("https://"), podcast.enlace)
