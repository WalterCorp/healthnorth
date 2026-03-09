"""URLs de l'application appointments — rendez-vous médicaux."""

from django.urls import path
from . import views

urlpatterns = [
    # Liste des rendez-vous du patient connecté
    path('', views.appointment_list, name='appointment_list'),
    # Prise d'un nouveau rendez-vous
    path('new/', views.appointment_new, name='appointment_new'),
    # Page de synthèse avant confirmation finale du rendez-vous
    path('confirm/', views.appointment_confirm, name='appointment_confirm'),
    # Annulation d'un rendez-vous — <int:appointment_id> = identifiant du RDV
    # Ex : /appointments/3/cancel/ annule le rendez-vous n°3
    path('<int:appointment_id>/cancel/', views.appointment_cancel, name='appointment_cancel'),
    # API JSON — retourne les examens filtrés par spécialité du spécialiste
    # Appelée en JavaScript lors du changement de spécialiste dans le formulaire
    path('api/exam-types/<int:specialist_id>/', views.api_exam_types, name='api_exam_types'),
    # API JSON — retourne les villes disponibles pour une région donnée
    # Appelée en JavaScript lors du changement de région dans le formulaire
    path('api/cities/<str:region>/', views.api_cities, name='api_cities'),
    # API JSON — retourne les cliniques disponibles pour une ville donnée
    # Appelée en JavaScript lors du changement de ville dans le formulaire
    path('api/clinics/<str:city>/', views.api_clinics, name='api_clinics'),
    # API JSON — retourne les spécialistes disponibles dans une clinique donnée
    # Appelée en JavaScript lors du changement de clinique dans le formulaire
    path('api/specialists/<int:clinic_id>/', views.api_specialists, name='api_specialists'),
]