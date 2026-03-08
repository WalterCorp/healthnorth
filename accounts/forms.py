"""Formulaires de l'application accounts."""

from django.contrib.auth.forms import UserCreationForm
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
        # Champs affichés dans le formulaire d'inscription
        # password1 = mot de passe, password2 = confirmation
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