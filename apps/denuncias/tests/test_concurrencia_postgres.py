"""Real PostgreSQL concurrency test for automatic assignment (S10).

This test is intentionally skipped unless the active database supports row-level
locking (``has_select_for_update``), so it does nothing on SQLite. It must be
run against a real PostgreSQL (local or the Railway instance) to validate the
``select_for_update()`` path with genuinely concurrent connections:

    DB_ENGINE=postgres POSTGRES_HOST=... python manage.py test \\
        apps.denuncias.tests.test_concurrencia_postgres

It launches one thread per report, all hitting the assignment service at the
same instant through independent connections.
"""

import threading

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from apps.core.tests.factories import documento_unico
from apps.denuncias.models import Denuncia
from apps.denuncias.services import asignar_profesional_automatico

Usuario = get_user_model()


@skipUnlessDBFeature("has_select_for_update")
class AsignacionConcurrentePostgresTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.duenio = Usuario.objects.create_user(
            email="conc-duenio@test.dev",
            password="Usuario123*",
            nombre_completo="Dueño Concurrencia",
            documento=documento_unico(),
            role="USUARIO",
        )

    def _crear_profesionales(self, cantidad: int) -> list:
        return [
            Usuario.objects.create_user(
                email=f"conc-prof-{i}@test.dev",
                password="Prof123*",
                nombre_completo=f"Prof Concurrencia {i}",
                documento=documento_unico(),
                role="PROFESIONAL",
            )
            for i in range(cantidad)
        ]

    def test_asignacion_concurrente_es_balanceada_y_completa(self):
        profesionales = self._crear_profesionales(3)
        denuncias = [
            Denuncia.objects.create(
                denunciante=self.duenio,
                modalidad="PUBLICA",
                tipo_situacion="ACOSO",
                descripcion="Descripción de prueba suficientemente larga.",
            )
            for _ in range(9)
        ]

        errores: list[str] = []
        barrera = threading.Barrier(len(denuncias))

        def asignar(denuncia: Denuncia) -> None:
            try:
                # All threads hit the assignment at (almost) the same instant.
                barrera.wait(timeout=15)
                asignar_profesional_automatico(denuncia)
            except Exception as error:  # noqa: BLE001 - surfaced in the assertion
                errores.append(repr(error))
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=asignar, args=(d,)) for d in denuncias]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=30)

        self.assertEqual(errores, [], "Ninguna asignación debe fallar")

        # 1) Every report ends up assigned exactly once.
        for denuncia in denuncias:
            denuncia.refresh_from_db()
            self.assertIsNotNone(denuncia.profesional_asignado_id)

        # 2) No report is assigned to two professionals (single FK) and the
        #    total matches: assignments are consistent.
        total = Denuncia.objects.filter(
            id__in=[d.id for d in denuncias], profesional_asignado__isnull=False
        ).count()
        self.assertEqual(total, len(denuncias))

        # 3) The distribution respects the "least loaded" criterion: with 9
        #    reports and 3 professionals every one gets exactly 3.
        conteos = [
            Denuncia.objects.filter(profesional_asignado=p).count() for p in profesionales
        ]
        self.assertEqual(sum(conteos), len(denuncias))
        self.assertLessEqual(
            max(conteos) - min(conteos),
            1,
            f"Distribución desbalanceada: {conteos}",
        )
