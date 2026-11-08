"""Shared DRF exceptions."""

from rest_framework.exceptions import APIException


class ConflictoDeEstado(APIException):
    """409 for writes that the resource's current state forbids.

    Used when a report is already finished: reading stays available, but no new
    interaction is allowed.
    """

    status_code = 409
    default_detail = (
        "Esta denuncia ha sido completada. Puedes consultar su información y el "
        "historial, pero ya no es posible realizar nuevas interacciones."
    )
    default_code = "denuncia_completada"
