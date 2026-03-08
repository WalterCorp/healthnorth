"""URLs de l'application appointments — rendez-vous médicaux."""

from django.urls import path
from . import views

urlpatterns = [
    # Liste des rendez-vous du patient connecté
    path('', views.appointment_list, name='appointment_list'),
    # Prise d'un nouveau rendez-vous
    path('new/', views.appointment_new, name='appointment_new'),
]