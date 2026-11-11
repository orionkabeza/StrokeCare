from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = "apps.common"
    label = "common"

    def ready(self):
        from . import converters  # noqa: F401  (registers the "patient" URL converter)
