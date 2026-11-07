"""Fictional in-memory files used by the upload tests."""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def png_bytes(size: tuple[int, int] = (16, 16)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (255, 86, 87)).save(buffer, format="PNG")
    return buffer.getvalue()


def imagen_png(nombre: str = "portada.png", size: tuple[int, int] = (16, 16)) -> SimpleUploadedFile:
    return SimpleUploadedFile(nombre, png_bytes(size), content_type="image/png")


def imagen_jpeg(nombre: str = "portada.jpg", size: tuple[int, int] = (16, 16)) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, (255, 202, 202)).save(buffer, format="JPEG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/jpeg")


def archivo_falso(nombre: str = "imagen.png", contenido: bytes = b"no soy una imagen") -> SimpleUploadedFile:
    return SimpleUploadedFile(nombre, contenido, content_type="image/png")


def archivo_grande(nombre: str = "grande.png", mb: float = 1.1) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        nombre, b"0" * int(mb * 1024 * 1024), content_type="image/png"
    )
