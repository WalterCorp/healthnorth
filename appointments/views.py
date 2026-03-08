"""Vues de l'application appointments — gestion des rendez-vous."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Appointment, Specialist, Specialty


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
    """Vue de prise d'un nouveau rendez-vous."""
    # Récupère tous les spécialistes et spécialités pour les afficher
    # dans le formulaire de sélection
    specialists = Specialist.objects.all()  # pylint: disable=no-member
    specialties = Specialty.objects.all()  # pylint: disable=no-member

    if request.method == 'POST':
        # Récupère les données du formulaire
        specialist_id = request.POST.get('specialist')
        date = request.POST.get('date')
        # Notes optionnelles — valeur par défaut = chaîne vide
        notes = request.POST.get('notes', '')

        # Crée le rendez-vous en base via l'ORM Django
        # Équivalent SQL : INSERT INTO appointments_appointment ...
        Appointment.objects.create(  # pylint: disable=no-member
            patient=request.user,
            specialist_id=specialist_id,
            date=date,
            notes=notes
        )
        messages.success(request, 'Rendez-vous pris avec succès !')
        # Redirige vers la liste des rendez-vous
        return redirect('appointment_list')

    # Affichage initial du formulaire avec les données disponibles
    return render(request, 'appointments/new.html', {
        'specialists': specialists,
        'specialties': specialties
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