"""Serializers for registration, authentication and user administration."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError

from apps.core.validators import validar_telefono
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

Usuario = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):
    """Public-safe representation of an account (never includes password)."""

    class Meta:
        model = Usuario
        fields = (
            "id",
            "email",
            "nombre_completo",
            "telefono",
            "documento",
            "direccion",
            "fecha_nacimiento",
            "role",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "email", "role", "is_active", "date_joined")


class RegisterSerializer(serializers.ModelSerializer):
    """Self-registration. New accounts always start with the USUARIO role."""

    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    # Declared explicitly so the friendly duplicate message (below) wins over
    # DRF's auto UniqueValidator wording, while keeping email format validation.
    email = serializers.EmailField()
    documento = serializers.CharField(max_length=40)

    class Meta:
        model = Usuario
        fields = (
            "email",
            "nombre_completo",
            "documento",
            "telefono",
            "password",
            "password_confirm",
        )

    def validate_email(self, value):
        email = value.lower()
        if Usuario.objects.filter(email=email).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo electrónico.")
        return email

    def validate_telefono(self, value):
        return validar_telefono(value)

    def validate_documento(self, value):
        # Whitespace-only values are rejected; uniqueness is also enforced by the
        # database constraint, so this is the friendly, early answer.
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("El número de documento es obligatorio.")
        # Case-insensitive so "ABC-1" and "abc-1" cannot coexist; the stored
        # value keeps its original case.
        if Usuario.objects.filter(documento__iexact=value).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta con este número de documento."
            )
        return value

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        # Validate with the account context so similarity to the email or the
        # name is also rejected, exactly like Django's password forms.
        usuario_temporal = Usuario(
            email=attrs.get("email", ""),
            nombre_completo=attrs.get("nombre_completo", ""),
        )
        try:
            validate_password(attrs["password"], user=usuario_temporal)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm", None)
        password = validated_data.pop("password")
        try:
            return Usuario.objects.create_user(password=password, **validated_data)
        except IntegrityError as error:
            # Closes the race between the uniqueness check and the insert: the
            # database constraint wins and the user still gets a structured 400
            # that identifies the offending field(s).
            detalle = str(error).lower()
            errores: dict[str, list[str]] = {}
            if "email" in detalle:
                errores["email"] = ["Ya existe una cuenta con este correo electrónico."]
            if "documento" in detalle:
                errores["documento"] = [
                    "Ya existe una cuenta con este número de documento."
                ]
            if not errores:
                errores["detail"] = [
                    "No fue posible completar el registro. Inténtalo nuevamente."
                ]
            raise serializers.ValidationError(errores)


class AdminUsuarioSerializer(serializers.ModelSerializer):
    """Administrator-only serializer: can change role and activation.

    The document is an identity field and stays immutable here too, so the
    profile rule cannot be bypassed through the administrative endpoint.
    """

    documento = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "email",
            "nombre_completo",
            "telefono",
            "documento",
            "role",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "email", "date_joined")

    def validate_telefono(self, value):
        return validar_telefono(value)

    def validate(self, attrs):
        # Reject an explicit attempt instead of silently dropping the field.
        if self.instance is not None and hasattr(self, "initial_data"):
            solicitado = self.initial_data.get("documento")
            if solicitado is not None and str(solicitado) != self.instance.documento:
                raise serializers.ValidationError(
                    {"documento": "El número de documento no se puede modificar."}
                )
        return attrs


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds role/email claims and returns the user alongside the tokens."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UsuarioSerializer(self.user).data
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Validates the new password with Django's own validators."""

    token = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        return attrs
