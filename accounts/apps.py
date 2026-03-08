"""Configuration de l'application accounts."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration principale de l'application accounts."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    # Nom affiché dans l'interface d'administration
    verbose_name = 'Comptes utilisateurs'