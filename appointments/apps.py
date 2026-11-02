"""Configuration de l'application appointments."""

from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    """Configuration principale de l'application appointments."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appointments'
    # Nom affiché dans l'interface d'administration
    verbose_name = 'Rendez-vous médicaux'

    def ready(self):
        """Enregistre les signaux (suppression des fichiers des documents)."""
        from . import signals  # noqa: F401  pylint: disable=import-outside-toplevel,unused-import