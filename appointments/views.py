"""Vues de l'application appointments — gestion des rendez-vous."""

from django.http import JsonResponse
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Appointment, Specialist, Specialty, ExamType, Clinic


# @login_required = décorateur de sécurité
# Si l'utilisateur n'est pas connecté, il est redirigé vers /accounts/login/
# automatiquement — protection côté serveur
@login_required
def appointment_list(request):
    """Liste des rendez-vous du patient connecté."""
    # Filtre les rendez-vous par patient connecté uniquement
    # Un patient ne peut jamais voir les rendez-vous d'un autre patient
    # order_by('-date') = du plus récent au plus ancien (- = décroissant)
    appointments = Appointment.objects.filter(  # pylint: disable=no-member
        patient=request.user
    ).order_by('-date')
    return render(request, 'appointments/list.html', {
        'appointments': appointments
    })


@login_required
def appointment_new(request):
    """Vue de prise d'un nouveau rendez-vous.

    Au lieu de créer directement le rendez-vous, on stocke les données
    en session et on redirige vers la page de synthèse.
    La session est un stockage côté serveur lié à l'utilisateur connecté.
    """
    # Récupère les régions disponibles depuis les REGION_CHOICES du modèle Clinic
    # dict.fromkeys() évite les doublons tout en gardant l'ordre
    regions = Clinic.REGION_CHOICES  # pylint: disable=no-member
    exam_types = ExamType.objects.all()  # pylint: disable=no-member

    if request.method == 'POST':
        # Récupère toutes les données du formulaire
        region = request.POST.get('region')
        city = request.POST.get('city')
        clinic_id = request.POST.get('clinic')
        specialist_id = request.POST.get('specialist')
        exam_type_id = request.POST.get('exam_type')
        date = request.POST.get('date')
        notes = request.POST.get('notes', '').strip()

        # Stocke les données en session pour les récupérer sur la page de synthèse
        request.session['appointment_data'] = {
            'region': region,
            'city': city,
            'clinic_id': clinic_id,
            'specialist_id': specialist_id,
            'exam_type_id': exam_type_id,
            'date': date,
            'notes': notes,
        }
        return redirect('appointment_confirm')

    return render(request, 'appointments/new.html', {
        # Liste des régions pour le premier select du formulaire
        'regions': regions,
        # Liste des examens — mis à jour dynamiquement après choix du spécialiste
        'exam_types': exam_types,
        # Formate la date au format attendu par datetime-local : "YYYY-MM-DDTHH:MM"
        'now': timezone.now().strftime('%Y-%m-%dT%H:%M'),
    })


@login_required
def appointment_confirm(request):
    """Vue de synthèse et confirmation finale du rendez-vous.

    Récupère les données stockées en session par appointment_new.
    Si la session est vide (accès direct à l'URL), redirige vers le formulaire.
    """
    appointment_data = request.session.get('appointment_data')

    if not appointment_data:
        messages.error(request, 'Veuillez d\'abord remplir le formulaire.')
        return redirect('appointment_new')

    # Récupère les objets liés pour afficher leurs informations dans la synthèse
    specialist = get_object_or_404(Specialist, id=appointment_data['specialist_id'])
    exam_type = get_object_or_404(ExamType, id=appointment_data['exam_type_id'])
    clinic = get_object_or_404(Clinic, id=appointment_data['clinic_id'])

    if request.method == 'POST':
        # L'utilisateur a confirmé — on crée le rendez-vous en base
        Appointment.objects.create(  # pylint: disable=no-member
            patient=request.user,
            specialist=specialist,
            exam_type=exam_type,
            clinic=clinic,
            date=appointment_data['date'],
            notes=appointment_data['notes'],
        )
        del request.session['appointment_data']
        messages.success(request, 'Rendez-vous confirmé avec succès !')
        return redirect('appointment_list')

    # strptime : convertit "2026-03-11T12:45" en objet datetime
    # strftime : reformate en "11/03/2026 12:45"
    date_formatee = datetime.strptime(
        appointment_data['date'], '%Y-%m-%dT%H:%M'
    ).strftime('%d/%m/%Y %H:%M')

    return render(request, 'appointments/confirm.html', {
        'specialist': specialist,
        'exam_type': exam_type,
        'clinic': clinic,
        'date': date_formatee,
        'notes': appointment_data['notes'],
    })


@login_required
def appointment_cancel(request, appointment_id):
    """Vue d'annulation d'un rendez-vous.

    get_object_or_404 : récupère le rendez-vous ou retourne une erreur 404
    La vérification patient=request.user empêche un patient d'annuler
    le rendez-vous d'un autre patient — sécurité importante.
    """
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user
    )
    appointment.status = 'cancelled'
    appointment.save()
    messages.success(request, 'Rendez-vous annulé.')
    return redirect('appointment_list')


@login_required
def api_exam_types(request, specialist_id):
    """Retourne les types d'examens liés à la spécialité du spécialiste en JSON.

    Appelée en AJAX depuis le formulaire de prise de rendez-vous.
    Permet de filtrer dynamiquement les examens selon le spécialiste choisi.
    """
    specialist = get_object_or_404(Specialist, id=specialist_id)
    exam_types = ExamType.objects.filter(  # pylint: disable=no-member
        specialty=specialist.specialty
    ).values('id', 'name', 'duration_minutes')
    return JsonResponse(list(exam_types), safe=False)


@login_required
def api_cities(request, region):
    """Retourne les villes disponibles pour une région donnée en JSON.

    Appelée en AJAX lors du changement de région dans le formulaire.
    distinct() évite les doublons si plusieurs cliniques sont dans la même ville.
    """
    # Filtre les cliniques par région et récupère les villes uniques
    # values_list('city', flat=True) retourne une liste de chaînes au lieu d'objets
    cities = Clinic.objects.filter(  # pylint: disable=no-member
        region=region
    ).values_list('city', flat=True).distinct().order_by('city')
    return JsonResponse(list(cities), safe=False)


@login_required
def api_clinics(request, city):
    """Retourne les cliniques disponibles pour une ville donnée en JSON.

    Appelée en AJAX lors du changement de ville dans le formulaire.
    """
    clinics = Clinic.objects.filter(  # pylint: disable=no-member
        city=city
    ).values('id', 'name', 'address')
    return JsonResponse(list(clinics), safe=False)


@login_required
def api_specialists(request, clinic_id):
    """Retourne les spécialistes disponibles dans une clinique donnée en JSON.

    Appelée en AJAX lors du changement de clinique dans le formulaire.
    clinics__id = filtre via la relation ManyToMany Specialist → Clinic
    """
    specialists = Specialist.objects.filter(  # pylint: disable=no-member
        clinics__id=clinic_id
    ).values('id', 'user__first_name', 'user__last_name', 'specialty__name')
    # Formate les données pour l'affichage dans le formulaire
    result = [
        {
            'id': s['id'],
            # Reconstruit "Dr. Nom" depuis les champs séparés
            'name': f"Dr. {s['user__last_name']}",
            'specialty': s['specialty__name'],
        }
        for s in specialists
    ]
    return JsonResponse(result, safe=False)