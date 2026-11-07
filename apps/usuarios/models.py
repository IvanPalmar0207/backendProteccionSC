"""User model and role definitions."""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class RolChoices(models.TextChoices):
    USUARIO = "USUARIO", "Usuario"
    PROFESIONAL = "PROFESIONAL", "Profesional"
    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"


class UsuarioManager(BaseUserManager):
    """Manager for the email-based custom user."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", RolChoices.USUARIO)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", RolChoices.ADMINISTRADOR)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Un superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superusuario debe tener is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Platform account. Identity data lives here and is never exposed to
    professionals for anonymous reports (see ``apps.denuncias``)."""

    email = models.EmailField("correo electrónico", unique=True)
    nombre_completo = models.CharField("nombre completo", max_length=150)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    documento = models.CharField("documento", max_length=40, blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    fecha_nacimiento = models.DateField("fecha de nacimiento", null=True, blank=True)
    role = models.CharField(
        "rol", max_length=20, choices=RolChoices.choices, default=RolChoices.USUARIO
    )
    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al admin", default=False)
    date_joined = models.DateTimeField("fecha de registro", default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre_completo"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def es_admin(self) -> bool:
        return self.role == RolChoices.ADMINISTRADOR

    @property
    def es_profesional(self) -> bool:
        return self.role == RolChoices.PROFESIONAL

    @property
    def es_usuario(self) -> bool:
        return self.role == RolChoices.USUARIO
