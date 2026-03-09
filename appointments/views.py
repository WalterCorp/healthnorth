"""Vues de l'application appointments — gestion des rendez-vous."""

from django.http import JsonResponse
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Appointment, Specialist, Specialty, ExamType, Clinic, Document


# @login_required = décorateur de sécurité
# Si l'utilisateur n'est pas connecté, il est redirigé vers /accounts/login/
# automatiquement — protection côté serveur
@login_required
def appointment_list(request):
    """Liste des rendez-vous du patient connecté."""
    appointments = Appointment.objects.filter(  # pylint: disable=no-member
        patient=request.user
    ).order_by('-date')
    return render(request, 'appointments/list.html', {
        'appointments': appointments
    })


@login_required
def appointment_new(request):
    """Vue de prise d'un nouveau rendez-vous."""
    regions = Clinic.REGION_CHOICES  # pylint: disable=no-member
    exam_types = ExamType.objects.all()  # pylint: disable=no-member

    if request.method == 'POST':
        region = request.POST.get('region')
        city = request.POST.get('city')
        clinic_id = request.POST.get('clinic')
        specialist_id = request.POST.get('specialist')
        exam_type_id = request.POST.get('exam_type')
        date = request.POST.get('date')
        notes = request.POST.get('notes', '').strip()

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
        'regions': regions,
        'exam_types': exam_types,
        'now': timezone.now().strftime('%Y-%m-%dT%H:%M'),
    })


@login_required
def appointment_confirm(request):
    """Vue de synthèse et confirmation finale du rendez-vous."""
    appointment_data = request.session.get('appointment_data')

    if not appointment_data:
        messages.error(request, 'Veuillez d\'abord remplir le formulaire.')
        return redirect('appointment_new')

    specialist = get_object_or_404(Specialist, id=appointment_data['specialist_id'])
    exam_type = get_object_or_404(ExamType, id=appointment_data['exam_type_id'])
    clinic = get_object_or_404(Clinic, id=appointment_data['clinic_id'])

    if request.method == 'POST':
        # Crée le rendez-vous en base
        appointment = Appointment.objects.create(  # pylint: disable=no-member
            patient=request.user,
            specialist=specialist,
            exam_type=exam_type,
            clinic=clinic,
            date=appointment_data['date'],
            notes=appointment_data['notes'],
        )
        del request.session['appointment_data']
        messages.success(request, 'Rendez-vous confirmé ! Vous pouvez déposer vos documents.')
        # Redirige vers la page de dépôt de documents au lieu de la liste
        return redirect('appointment_documents', appointment_id=appointment.id)

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
def appointment_documents(request, appointment_id):
    """Vue de dépôt de documents pour un rendez-vous confirmé.

    Permet au patient de déposer une ordonnance, un certificat médical
    ou tout autre document lié à son rendez-vous.
    La vérification patient=request.user empêche un patient d'accéder
    aux documents d'un autre patient.
    """
    # Récupère le rendez-vous — vérifie qu'il appartient au patient connecté
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user
    )
    # Récupère les documents déjà déposés pour ce rendez-vous
    documents = appointment.documents.all()

    if request.method == 'POST':
        # Récupère le type de document et le fichier depuis le formulaire
        document_type = request.POST.get('document_type')
        # request.FILES contient les fichiers uploadés — différent de request.POST
        file = request.FILES.get('file')

        if file:
            # Crée le document en base et sauvegarde le fichier dans media/documents/
            Document.objects.create(  # pylint: disable=no-member
                appointment=appointment,
                document_type=document_type,
                file=file,
            )
            messages.success(request, 'Document déposé avec succès !')
            # Recharge la page pour afficher le nouveau document
            return redirect('appointment_documents', appointment_id=appointment.id)
        else:
            messages.error(request, 'Veuillez sélectionner un fichier.')

    return render(request, 'appointments/documents.html', {
        'appointment': appointment,
        # Choices pour le select du type de document
        'document_types': Document.DOCUMENT_TYPE_CHOICES,
        # Documents déjà déposés
        'documents': documents,
    })


@login_required
def appointment_cancel(request, appointment_id):
    """Vue d'annulation d'un rendez-vous."""
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
    """Retourne les types d'examens liés à la spécialité du spécialiste en JSON."""
    specialist = get_object_or_404(Specialist, id=specialist_id)
    exam_types = ExamType.objects.filter(  # pylint: disable=no-member
        specialty=specialist.specialty
    ).values('id', 'name', 'duration_minutes')
    return JsonResponse(list(exam_types), safe=False)


@login_required
def api_cities(request, region):
    """Retourne les villes disponibles pour une région donnée en JSON."""
    cities = Clinic.objects.filter(  # pylint: disable=no-member
        region=region
    ).values_list('city', flat=True).distinct().order_by('city')
    return JsonResponse(list(cities), safe=False)


@login_required
def api_clinics(request, city):
    """Retourne les cliniques disponibles pour une ville donnée en JSON."""
    clinics = Clinic.objects.filter(  # pylint: disable=no-member
        city=city
    ).values('id', 'name', 'address')
    return JsonResponse(list(clinics), safe=False)


@login_required
def api_specialists(request, clinic_id):
    """Retourne les spécialistes disponibles dans une clinique donnée en JSON."""
    specialists = Specialist.objects.filter(  # pylint: disable=no-member
        clinics__id=clinic_id
    ).values('id', 'user__first_name', 'user__last_name', 'specialty__name')
    result = [
        {
            'id': s['id'],
            'name': f"Dr. {s['user__last_name']}",
            'specialty': s['specialty__name'],
        }
        for s in specialists
    ]
    return JsonResponse(result, safe=False)