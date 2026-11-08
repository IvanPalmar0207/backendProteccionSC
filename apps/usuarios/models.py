"""User model and role definitions."""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.validators import validar_fecha_nacimiento


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
        # The document is a mandatory identity field: no creation path may
        # produce an account without one (an empty string would be a valid,
        # and therefore colliding, unique value).
        documento = (extra_fields.get("documento") or "").strip()
        if not documento:
            raise ValueError("El número de documento es obligatorio.")
        extra_fields["documento"] = documento
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
    # Mandatory, unique identity field. Kept as text to preserve leading zeros.
    documento = models.CharField("documento", max_length=40, unique=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    fecha_nacimiento = models.DateField(
        "fecha de nacimiento",
        null=True,
        blank=True,
        validators=[validar_fecha_nacimiento],
    )
    role = models.CharField(
        "rol", max_length=20, choices=RolChoices.choices, default=RolChoices.USUARIO
    )
    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al admin", default=False)
    date_joined = models.DateTimeField("fecha de registro", default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre_completo", "documento"]

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


class TokenRecuperacion(models.Model):
    """Single-use password recovery token.

    Only the SHA-256 hash of the token is stored, so a database leak does not
    expose usable recovery links. A token is valid until it expires or is
    consumed, whichever comes first.
    """

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="tokens_recuperacion",
        verbose_name="usuario",
    )
    token_hash = models.CharField("hash del token", max_length=64, unique=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    expira_en = models.DateTimeField("expira en")
    usado = models.BooleanField("usado", default=False)

    class Meta:
        verbose_name = "token de recuperación"
        verbose_name_plural = "tokens de recuperación"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Token de {self.usuario_id} ({'usado' if self.usado else 'vigente'})"

    @property
    def vigente(self) -> bool:
        return not self.usado and self.expira_en > timezone.now()
