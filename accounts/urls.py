"""URLs de l'application accounts — inscription, connexion, déconnexion."""

from django.urls import path
from . import views

urlpatterns = [
    # Page d'inscription
    path('register/', views.register, name='register'),
    # Page de connexion
    path('login/', views.login_view, name='login'),
    # Déconnexion
    path('logout/', views.logout_view, name='logout'),
]