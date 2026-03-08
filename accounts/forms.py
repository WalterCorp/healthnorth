"""Formulaires de l'application accounts."""

from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User


class RegisterForm(UserCreationForm):
    """Formulaire d'inscription d'un nouvel utilisateur.

    Étend UserCreationForm qui gère déjà :
    - La validation du mot de passe
    - La vérification que les deux mots de passe correspondent
    - La vérification que le nom d'utilisateur est unique
    """

    class Meta:
        """Options du formulaire."""

        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'date_of_birth',
            'password1',
            'password2'
        ]
        # Labels personnalisés en français pour nos champs
        labels = {
            'phone': 'Téléphone',
            'address': 'Adresse',
            'date_of_birth': 'Date de naissance',
        }


class ProfileForm(UserChangeForm):
    """Formulaire de modification du profil utilisateur.

    Étend UserChangeForm qui gère déjà la modification
    des informations de base de l'utilisateur.
    On masque le champ password car il est géré séparément.
    """

    # On masque le champ password — géré via une vue dédiée
    password = None

    class Meta:
        """Options du formulaire."""

        model = User
        # Champs modifiables par l'utilisateur
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'date_of_birth',
        ]
        # Labels en français
        labels = {
            'phone': 'Téléphone',
            'address': 'Adresse',
            'date_of_birth': 'Date de naissance',
        }