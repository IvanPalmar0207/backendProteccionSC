"""Report business operations: balanced professional assignment.

Assignment always happens in the backend. The professional with the fewest
*active* cases is chosen (deterministic tie-break by id), and the candidate
rows are locked so concurrent creations cannot resolve inconsistently.
"""

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import Count, Q

from apps.core.exceptions import ConflictoDeEstado

from .models import EstadoChoices, SeguimientoDenuncia

Usuario = get_user_model()

ROL_PROFESIONAL = "PROFESIONAL"


def profesionales_habilitados():
    """Active professionals ordered by current active-case load.

    "Active case" = assigned report not finished. The order is deterministic
    (fewest active cases first, then lowest id) so ties are always resolved the
    same way.
    """
    return (
        Usuario.objects.filter(role=ROL_PROFESIONAL, is_active=True)
        .annotate(
            casos_activos=Count(
                "denuncias_asignadas",
                filter=~Q(denuncias_asignadas__estado=EstadoChoices.FINALIZADA),
            )
        )
        .order_by("casos_activos", "id")
    )


def asignar_profesional_automatico(denuncia):
    """Assign the least-loaded active professional, or ``None`` if there is none.

    Runs inside a transaction and, where the backend supports it, locks the
    candidate rows so two simultaneous reports are serialized.
    """
    with transaction.atomic():
        candidatos = Usuario.objects.filter(role=ROL_PROFESIONAL, is_active=True)
        if connection.features.has_select_for_update:
            candidatos = candidatos.select_for_update()
        ids = list(candidatos.order_by("id").values_list("id", flat=True))
        if not ids:
            return None

        elegido = (
            Usuario.objects.filter(id__in=ids)
            .annotate(
                casos_activos=Count(
                    "denuncias_asignadas",
                    filter=~Q(denuncias_asignadas__estado=EstadoChoices.FINALIZADA),
                )
            )
            .order_by("casos_activos", "id")
            .first()
        )
        if elegido is None:
            return None

        estado_anterior = denuncia.estado
        denuncia.profesional_asignado = elegido
        if denuncia.estado == EstadoChoices.PENDIENTE:
            denuncia.estado = EstadoChoices.EN_PROCESO
        denuncia.save(update_fields=["profesional_asignado", "estado", "actualizado_en"])
        SeguimientoDenuncia.objects.create(
            denuncia=denuncia,
            autor=None,
            estado_anterior=estado_anterior,
            estado_nuevo=denuncia.estado,
            observacion=f"Caso asignado automáticamente a {elegido.nombre_completo}.",
        )
        return elegido


def esta_finalizada(denuncia) -> bool:
    return denuncia.estado == EstadoChoices.FINALIZADA


def asegurar_editable(denuncia) -> None:
    """Reject writes on a finished report with a 409 Conflict."""
    if esta_finalizada(denuncia):
        raise ConflictoDeEstado()


def refrescar_seguimientos(denuncia) -> None:
    """Invalidate the prefetched follow-up cache after adding an entry.

    Without this the (prefetched) serializer would return the stale history.
    """
    cache = getattr(denuncia, "_prefetched_objects_cache", None)
    if cache is not None:
        cache.pop("seguimientos", None)


def registrar_pendiente_de_asignacion(denuncia) -> None:
    """Log that the report is waiting for an available professional."""
    SeguimientoDenuncia.objects.create(
        denuncia=denuncia,
        autor=None,
        estado_anterior=denuncia.estado,
        estado_nuevo=denuncia.estado,
        observacion="Pendiente de asignación: no hay profesionales disponibles.",
    )
