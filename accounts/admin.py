"""Configuration de l'administration pour l'application accounts."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


# On étend UserAdmin pour garder toutes les fonctionnalités
# de gestion des utilisateurs Django (mot de passe, permissions, etc.)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Administration du modèle User personnalisé."""

    # Colonnes affichées dans la liste des utilisateurs
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    # Champs supplémentaires dans le formulaire d'édition
    fieldsets = UserAdmin.fieldsets + (
        ('Informations médicales', {
            'fields': ('phone', 'address', 'date_of_birth')
        }),
    )