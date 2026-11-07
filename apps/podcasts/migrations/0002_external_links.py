"""Refactor podcasts to externally hosted episodes (validated HTTPS links).

The `enlace` field is required at the API level; it is added with a one-off
default (``preserve_default=False``) so existing rows can be migrated without
keeping a database default.
"""

import django.utils.timezone
from django.db import migrations, models

import apps.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("podcasts", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(model_name="podcast", name="audio"),
        migrations.RemoveField(model_name="podcast", name="audio_url"),
        migrations.RemoveField(model_name="podcast", name="duracion_segundos"),
        migrations.AddField(
            model_name="podcast",
            name="programa",
            field=models.CharField(blank=True, max_length=150, verbose_name="programa"),
        ),
        migrations.AddField(
            model_name="podcast",
            name="plataforma",
            field=models.CharField(
                choices=[
                    ("SPOTIFY", "Spotify"),
                    ("YOUTUBE", "YouTube"),
                    ("APPLE_PODCASTS", "Apple Podcasts"),
                    ("OTRA", "Otra"),
                ],
                default="OTRA",
                max_length=20,
                verbose_name="plataforma",
            ),
        ),
        migrations.AddField(
            model_name="podcast",
            name="enlace",
            field=models.URLField(
                default="",
                help_text="URL HTTPS del episodio en su plataforma de origen.",
                max_length=500,
                validators=[apps.core.validators.validar_enlace_https],
                verbose_name="enlace del episodio",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="podcast",
            name="portada",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="podcasts/portadas/",
                validators=[apps.core.validators.validar_imagen],
                verbose_name="portada",
            ),
        ),
        migrations.AlterField(
            model_name="podcast",
            name="fecha_publicacion",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="fecha de publicación"
            ),
        ),
    ]
