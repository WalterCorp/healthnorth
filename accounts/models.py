"""Modèles de l'application accounts — gestion des utilisateurs."""

from django.contrib.auth.models import AbstractUser
from django.db import models


# On étend le modèle utilisateur par défaut de Django
# AbstractUser fournit déjà : email, password, first_name, last_name
# On ajoute nos champs spécifiques au projet
class User(AbstractUser):
    """Modèle utilisateur étendu avec informations médicales."""

    # Résolution des conflits avec auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name='accounts_user_set'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='accounts_user_set'
    )

    # Numéro de téléphone du patient
    phone = models.CharField(max_length=20, blank=True)
    # Adresse postale
    address = models.TextField(blank=True)
    # Date de naissance (optionnelle)
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self) -> str:
        """Représentation lisible de l'objet."""
        return str(f"{self.first_name} {self.last_name}")