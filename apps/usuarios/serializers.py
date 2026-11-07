"""Serializers for registration, authentication and user administration."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
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

    class Meta:
        model = Usuario
        fields = (
            "email",
            "nombre_completo",
            "telefono",
            "password",
            "password_confirm",
        )

    def validate_email(self, value):
        email = value.lower()
        if Usuario.objects.filter(email=email).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo electrónico.")
        return email

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
        return Usuario.objects.create_user(password=password, **validated_data)


class AdminUsuarioSerializer(serializers.ModelSerializer):
    """Administrator-only serializer: can change role and activation."""

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
