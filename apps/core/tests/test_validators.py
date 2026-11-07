"""Tests for the shared validators (F2-S14)."""

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings

from apps.core.tests.factories import archivo_falso, archivo_grande, imagen_png
from apps.core.validators import validar_enlace_https, validar_imagen


class ValidarEnlaceTests(SimpleTestCase):
    def test_accepts_https(self):
        validar_enlace_https("https://open.spotify.com/episode/1")  # no raise

    def test_rejects_http(self):
        with self.assertRaises(ValidationError):
            validar_enlace_https("http://example.com/a.mp3")

    def test_rejects_other_schemes(self):
        for enlace in ("ftp://x", "javascript:alert(1)", "data:text/html,x"):
            with self.assertRaises(ValidationError):
                validar_enlace_https(enlace)


class ValidarImagenTests(SimpleTestCase):
    def test_accepts_valid_png(self):
        validar_imagen(imagen_png())  # no raise

    def test_rejects_unknown_extension(self):
        with self.assertRaises(ValidationError):
            validar_imagen(archivo_falso("script.txt"))

    def test_rejects_mime_mismatch(self):
        archivo = imagen_png("foto.png")
        archivo.content_type = "application/pdf"
        with self.assertRaises(ValidationError):
            validar_imagen(archivo)

    def test_rejects_fake_image(self):
        with self.assertRaises(ValidationError):
            validar_imagen(archivo_falso("falsa.png"))

    @override_settings(MAX_IMAGE_UPLOAD_MB=1)
    def test_rejects_oversized_file(self):
        with self.assertRaises(ValidationError):
            validar_imagen(archivo_grande(mb=1.2))
