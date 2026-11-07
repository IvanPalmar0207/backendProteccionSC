"""Idempotent demo-data seeding.

Running ``python manage.py seed_demo`` repeatedly must not create duplicates.
Every object is looked up by a natural key (email, title, ...) before creation.
All data is fictional: no real victim information is used.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.chat.models import Conversacion, Mensaje
from apps.denuncias.models import (
    Denuncia,
    EstadoChoices,
    ModalidadChoices,
    SeguimientoDenuncia,
    TipoSituacionChoices,
)
from apps.foro.models import Publicacion, Respuesta
from apps.noticias.models import Noticia
from apps.podcasts.models import Podcast

Usuario = get_user_model()

CUENTAS = [
    {
        "email": "usuario@proteccioninmediata.test",
        "password": "Usuario123*",
        "nombre_completo": "Valentina Gómez",
        "telefono": "3001234567",
        "documento": "1000000001",
        "role": "USUARIO",
    },
    {
        "email": "profesional@proteccioninmediata.test",
        "password": "Profesional123*",
        "nombre_completo": "Dra. Camila Restrepo",
        "telefono": "3007654321",
        "documento": "1000000002",
        "role": "PROFESIONAL",
    },
    {
        "email": "admin@proteccioninmediata.test",
        "password": "Admin123*",
        "nombre_completo": "Andrés Administrador",
        "telefono": "3009998888",
        "documento": "1000000003",
        "role": "ADMINISTRADOR",
    },
]

NOTICIAS = [
    {
        "titulo": "Rutas de atención inmediata en tu ciudad",
        "resumen": "Conocé los canales disponibles para pedir ayuda.",
        "contenido": (
            "Protección Inmediata SC centraliza las rutas de atención para que "
            "encuentres acompañamiento profesional sin exponer tu identidad si "
            "no lo deseás."
        ),
    },
    {
        "titulo": "Cómo identificar una situación de violencia intrafamiliar",
        "resumen": "Señales de alerta y primeros pasos.",
        "contenido": (
            "Reconocer las señales es el primer paso. Esta guía resume indicadores "
            "y recuerda que denunciar de forma anónima también es posible."
        ),
    },
    {
        "titulo": "El acompañamiento psicosocial durante el proceso",
        "resumen": "Qué esperar de un profesional de apoyo.",
        "contenido": (
            "Un profesional puede orientarte, escucharte y ayudarte a tomar "
            "decisiones sin presionarte."
        ),
    },
]

PODCASTS = [
    {
        "titulo": "Episodio 1: Romper el silencio",
        "descripcion": "Conversación sobre el primer paso para pedir ayuda.",
        "audio_url": "https://example.com/podcasts/episodio-1.mp3",
        "duracion_segundos": 1450,
    },
    {
        "titulo": "Episodio 2: Redes de apoyo",
        "descripcion": "Cómo construir una red de apoyo segura.",
        "audio_url": "https://example.com/podcasts/episodio-2.mp3",
        "duracion_segundos": 1210,
    },
]

PUBLICACIONES = [
    {
        "titulo": "Bienvenida al foro de acompañamiento",
        "contenido": "Este es un espacio seguro. Respetemos a quienes comparten.",
    },
    {
        "titulo": "¿Cómo contarle a una persona de confianza?",
        "contenido": "Comparto mi experiencia pidiendo ayuda por primera vez.",
    },
]


class Command(BaseCommand):
    help = "Crea las cuentas de prueba y datos ficticios de demostración (idempotente)."

    @transaction.atomic
    def handle(self, *args, **options):
        admin = self._crear_cuentas()
        self._crear_noticias(admin)
        self._crear_podcasts(admin)
        self._crear_foro()
        self._crear_denuncias()
        self._crear_conversacion()
        self.stdout.write(self.style.SUCCESS("Datos de demostración listos."))

    # -- helpers ----------------------------------------------------------
    def _crear_cuentas(self):
        cuentas = {}
        for datos in CUENTAS:
            password = datos["password"]
            defaults = {k: v for k, v in datos.items() if k not in ("email", "password")}
            usuario, creado = Usuario.objects.get_or_create(
                email=datos["email"], defaults=defaults
            )
            if creado or not usuario.check_password(password):
                usuario.set_password(password)
            # Keep role/identity in sync on every run.
            usuario.role = datos["role"]
            usuario.nombre_completo = datos["nombre_completo"]
            usuario.telefono = datos["telefono"]
            usuario.documento = datos["documento"]
            usuario.is_active = True
            if datos["role"] == "ADMINISTRADOR":
                usuario.is_staff = True
                usuario.is_superuser = True
            usuario.save()
            cuentas[datos["role"]] = usuario
        return cuentas["ADMINISTRADOR"]

    def _crear_noticias(self, admin):
        for datos in NOTICIAS:
            Noticia.objects.get_or_create(
                titulo=datos["titulo"],
                defaults={**datos, "autor": admin, "publicado": True},
            )

    def _crear_podcasts(self, admin):
        for datos in PODCASTS:
            Podcast.objects.get_or_create(
                titulo=datos["titulo"],
                defaults={**datos, "autor": admin, "publicado": True},
            )

    def _crear_foro(self):
        usuario = Usuario.objects.get(email="usuario@proteccioninmediata.test")
        for datos in PUBLICACIONES:
            publicacion, _ = Publicacion.objects.get_or_create(
                titulo=datos["titulo"], defaults={**datos, "autor": usuario}
            )
            Respuesta.objects.get_or_create(
                publicacion=publicacion,
                autor=usuario,
                contenido="Gracias por compartir, a mí me pasó algo parecido.",
            )

    def _crear_denuncias(self):
        usuario = Usuario.objects.get(email="usuario@proteccioninmediata.test")
        profesional = Usuario.objects.get(email="profesional@proteccioninmediata.test")

        publica_marca = "[demo] Situación en el hogar"
        if not Denuncia.objects.filter(denunciante=usuario, descripcion__startswith=publica_marca).exists():
            publica = Denuncia.objects.create(
                denunciante=usuario,
                modalidad=ModalidadChoices.PUBLICA,
                tipo_situacion=TipoSituacionChoices.VIOLENCIA_INTRAFAMILIAR,
                descripcion=publica_marca + ": hechos ficticios de demostración.",
                ubicacion="Bogotá",
                estado=EstadoChoices.EN_PROCESO,
                profesional_asignado=profesional,
            )
            SeguimientoDenuncia.objects.create(
                denuncia=publica,
                autor=usuario,
                estado_nuevo=EstadoChoices.PENDIENTE,
                observacion="Denuncia registrada.",
            )
            SeguimientoDenuncia.objects.create(
                denuncia=publica,
                autor=profesional,
                estado_anterior=EstadoChoices.PENDIENTE,
                estado_nuevo=EstadoChoices.EN_PROCESO,
                observacion="Caso asignado para acompañamiento.",
            )

        anonima_marca = "[demo] Hechos de acoso"
        if not Denuncia.objects.filter(denunciante=usuario, descripcion__startswith=anonima_marca).exists():
            Denuncia.objects.create(
                denunciante=usuario,
                modalidad=ModalidadChoices.ANONIMA,
                tipo_situacion=TipoSituacionChoices.ACOSO,
                descripcion=anonima_marca + ": relato ficticio de demostración.",
                estado=EstadoChoices.PENDIENTE,
            )

    def _crear_conversacion(self):
        usuario = Usuario.objects.get(email="usuario@proteccioninmediata.test")
        profesional = Usuario.objects.get(email="profesional@proteccioninmediata.test")
        denuncia = (
            Denuncia.objects.filter(denunciante=usuario, modalidad=ModalidadChoices.PUBLICA)
            .order_by("id")
            .first()
        )
        if denuncia is None:
            return
        conversacion, _ = Conversacion.objects.get_or_create(denuncia=denuncia)
        conversacion.participantes.add(usuario, profesional)
        if not conversacion.mensajes.exists():
            Mensaje.objects.create(
                conversacion=conversacion,
                remitente=usuario,
                contenido="Hola, necesito orientación sobre mi caso.",
            )
            Mensaje.objects.create(
                conversacion=conversacion,
                remitente=profesional,
                contenido="Hola, estoy para acompañarte. ¿Cómo te sentís hoy?",
            )
