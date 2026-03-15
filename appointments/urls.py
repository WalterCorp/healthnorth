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
    # Modification d'un rendez-vous (date et notes)
    path('<int:appointment_id>/edit/', views.appointment_edit, name='appointment_edit'),
    # Annulation d'un rendez-vous
    path('<int:appointment_id>/cancel/', views.appointment_cancel, name='appointment_cancel'),
    # Dépôt de documents pour un rendez-vous confirmé
    path('<int:appointment_id>/documents/', views.appointment_documents, name='appointment_documents'),
    # API CRUD — liste et création de rendez-vous
    path('api/appointments/', views.api_appointments, name='api_appointments'),
    # API CRUD — détail, modification et suppression d'un rendez-vous
    path('api/appointments/<int:appointment_id>/', views.api_appointment_detail, name='api_appointment_detail'),
    # API JSON — examens filtrés par spécialité du spécialiste
    path('api/exam-types/<int:specialist_id>/', views.api_exam_types, name='api_exam_types'),
    # API JSON — villes disponibles pour une région donnée
    path('api/cities/<str:region>/', views.api_cities, name='api_cities'),
    # API JSON — cliniques disponibles pour une ville donnée
    path('api/clinics/<str:city>/', views.api_clinics, name='api_clinics'),
    # API JSON — spécialistes disponibles dans une clinique donnée
    path('api/specialists/<int:clinic_id>/', views.api_specialists, name='api_specialists'),
]
