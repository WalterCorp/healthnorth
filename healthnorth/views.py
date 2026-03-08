"""Vues principales du projet healthnorth."""

from django.shortcuts import render


def home(request):
    """Page d'accueil du site."""
    return render(request, 'home.html')