from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        self._configure_pillow_limits()

    @staticmethod
    def _configure_pillow_limits():
        """
        Cap the pixel count Pillow will decode.

        Uploads are parsed by Pillow before anyone is allowed to look at them,
        so a small crafted file that expands to gigabytes of bitmap is a cheap
        way to exhaust a worker. Pillow ships a default, but it is silent and
        easy to lose track of — pin it explicitly, and make it tunable, because
        legitimate medical images can be large (a 4k x 4k radiograph is ~17M
        pixels; the 200M default here leaves generous headroom).
        """
        try:
            from PIL import Image
        except ImportError:  # pragma: no cover - Pillow is a hard dependency
            return
        Image.MAX_IMAGE_PIXELS = getattr(settings, 'PILLOW_MAX_IMAGE_PIXELS', 200_000_000)
