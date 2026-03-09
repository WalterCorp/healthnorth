"""Vues de l'application appointments — gestion des rendez-vous."""

from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Appointment, Specialist, Specialty, ExamType


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
    # Envoie la liste au template
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
    specialists = Specialist.objects.all()  # pylint: disable=no-member
    specialties = Specialty.objects.all()  # pylint: disable=no-member
    # Récupère tous les types d'examens pour le formulaire
    exam_types = ExamType.objects.all()  # pylint: disable=no-member

    if request.method == 'POST':
        # Récupère les données du formulaire
        specialist_id = request.POST.get('specialist')
        exam_type_id = request.POST.get('exam_type')
        date = request.POST.get('date')
        notes = request.POST.get('notes', '').strip()

        # Stocke les données en session pour les récupérer sur la page de synthèse
        # La session évite de passer les données sensibles dans l'URL
        request.session['appointment_data'] = {
            'specialist_id': specialist_id,
            'exam_type_id': exam_type_id,
            'date': date,
            'notes': notes,
        }
        # Redirige vers la page de synthèse au lieu de créer directement le RDV
        return redirect('appointment_confirm')

    return render(request, 'appointments/new.html', {
        'specialists': specialists,
        'specialties': specialties,
        # Liste des types d'examens pour le formulaire
        'exam_types': exam_types,
        # Formate la date au format attendu par datetime-local : "YYYY-MM-DDTHH:MM"
        # Empêche l'utilisateur de choisir une date dans le passé
        'now': timezone.now().strftime('%Y-%m-%dT%H:%M'),
    })


@login_required
def appointment_confirm(request):
    """Vue de synthèse et confirmation finale du rendez-vous.

    Récupère les données stockées en session par appointment_new.
    Si la session est vide (accès direct à l'URL), redirige vers le formulaire.
    """
    # Récupère les données stockées en session
    appointment_data = request.session.get('appointment_data')

    # Si pas de données en session — accès direct à l'URL sans passer par le formulaire
    if not appointment_data:
        messages.error(request, 'Veuillez d\'abord remplir le formulaire.')
        return redirect('appointment_new')

    # Récupère le spécialiste pour afficher ses informations dans la synthèse
    specialist = get_object_or_404(Specialist, id=appointment_data['specialist_id'])
    # Récupère le type d'examen pour afficher ses informations dans la synthèse
    exam_type = get_object_or_404(ExamType, id=appointment_data['exam_type_id'])

    if request.method == 'POST':
        # L'utilisateur a confirmé — on crée le rendez-vous en base
        # Équivalent SQL : INSERT INTO appointments_appointment ...
        Appointment.objects.create(  # pylint: disable=no-member
            patient=request.user,
            specialist=specialist,
            exam_type=exam_type,
            date=appointment_data['date'],
            notes=appointment_data['notes'],
        )
        # Supprime les données de session — elles ne sont plus nécessaires
        del request.session['appointment_data']
        messages.success(request, 'Rendez-vous confirmé avec succès !')
        return redirect('appointment_list')

    # strptime : convertit la chaîne "2026-03-11T12:45" en objet datetime
    # strftime : reformate l'objet datetime en "11/03/2026 12:45"
    date_formatee = datetime.strptime(
        appointment_data['date'], '%Y-%m-%dT%H:%M'
    ).strftime('%d/%m/%Y %H:%M')

    # Affichage de la synthèse avec les données du rendez-vous
    return render(request, 'appointments/confirm.html', {
        'specialist': specialist,
        # Type d'examen sélectionné
        'exam_type': exam_type,
        # date_formatee : version lisible pour l'affichage
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
    # Récupère le rendez-vous — vérifie qu'il appartient bien au patient connecté
    # Équivalent SQL : SELECT * FROM appointments WHERE id=X AND patient_id=Y
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user
    )
    # Met à jour le statut — Équivalent SQL : UPDATE appointments SET status='cancelled'
    appointment.status = 'cancelled'
    appointment.save()
    messages.success(request, 'Rendez-vous annulé.')
    return redirect('appointment_list')