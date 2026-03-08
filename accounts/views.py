"""Vues de l'application accounts — inscription, connexion, déconnexion."""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegisterForm, ProfileForm


def register(request):
    """Vue d'inscription d'un nouvel utilisateur."""
    # Si le formulaire est soumis (méthode POST)
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        # Vérifie que les données sont valides (mot de passe, champs requis, etc.)
        if form.is_valid():
            # Sauvegarde l'utilisateur en base de données
            user = form.save()
            # Connecte automatiquement l'utilisateur après inscription
            # Évite à l'utilisateur de se reconnecter manuellement
            login(request, user)
            messages.success(request, 'Compte créé avec succès !')
            # Redirige vers la page d'accueil
            return redirect('home')
    else:
        # Affichage initial — formulaire vide (méthode GET)
        form = RegisterForm()
    # Envoie le formulaire au template
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Vue de connexion d'un utilisateur existant."""
    if request.method == 'POST':
        # AuthenticationForm vérifie automatiquement username + password
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            # Récupère l'objet utilisateur validé
            user = form.get_user()
            # Crée la session utilisateur
            login(request, user)
            messages.success(request, f'Bienvenue {user.first_name} !')
            return redirect('home')
    else:
        # Formulaire vide à l'affichage initial
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Vue de déconnexion — détruit la session utilisateur."""
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    # Redirige vers la page de connexion
    return redirect('login')


@login_required
def profile(request):
    """Vue de modification du profil utilisateur."""
    if request.method == 'POST':
        # On passe instance=request.user pour modifier l'utilisateur existant
        # Sans instance, Django créerait un nouvel utilisateur (INSERT)
        # Avec instance, Django met à jour l'utilisateur existant (UPDATE)
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès !')
            return redirect('profile')
    else:
        # Pré-remplit le formulaire avec les données actuelles de l'utilisateur
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})