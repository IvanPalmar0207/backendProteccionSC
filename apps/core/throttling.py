"""Shared throttling classes."""

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle


class PasswordResetThrottle(AnonRateThrottle):
    """Per-IP rate limit for password recovery.

    The rate comes from the Django ``PASSWORD_RESET_RATE`` setting rather than
    DRF's ``DEFAULT_THROTTLE_RATES`` so it can be reconfigured (and overridden
    in tests) without reloading the DRF API settings singleton.
    """

    scope = "password_reset"

    def get_rate(self) -> str:
        return getattr(settings, "PASSWORD_RESET_RATE", "5/hour")
