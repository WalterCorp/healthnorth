"""Vues de l'application appointments — gestion des rendez-vous."""

import mimetypes
import os

from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django import forms
from .forms import AppointmentDateField, AppointmentEditForm, AppointmentForm, DocumentUploadForm
from .models import Appointment, Specialist, Specialty, ExamType, Clinic, Document

# Types de fichiers affichés directement dans le navigateur (stockage local) —
# tout autre type est téléchargé, pour qu'aucun fichier ne s'exécute sur le domaine du site
INLINE_CONTENT_TYPES = {'application/pdf', 'image/jpeg', 'image/png'}


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

    # Choix des listes en cascade à resélectionner après une erreur (vide au premier affichage)
    selection = {}

    if request.method == 'POST':
        # Validation côté serveur : champs obligatoires, format de date, date future
        form = AppointmentForm(request.POST)
        if form.is_valid():
            # Seules des données validées sont conservées en session jusqu'à la confirmation
            request.session['appointment_data'] = form.session_data()
            return redirect('appointment_confirm')
        # Formulaire invalide : renvoie les identifiants choisis pour restaurer la cascade
        selection = {
            key: request.POST.get(key, '')
            for key in ('region', 'city', 'clinic', 'specialist', 'exam_type')
        }
    else:
        form = AppointmentForm()

    return render(request, 'appointments/new.html', {
        # Formulaire (avec ses éventuelles erreurs de validation)
        'form': form,
        # Choix à resélectionner dans les listes en cascade (sérialisés par json_script)
        'selection': selection,
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

    # Revalidation : les données en session peuvent être devenues invalides
    # (date passée entre-temps, ancien format de session, spécialiste supprimé…)
    form = AppointmentForm(appointment_data)
    if not form.is_valid():
        del request.session['appointment_data']
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect('appointment_new')
    data = form.cleaned_data

    if request.method == 'POST':
        # Crée le rendez-vous en base
        appointment = Appointment.objects.create(  # pylint: disable=no-member
            patient=request.user,
            specialist=data['specialist'],
            exam_type=data['exam_type'],
            clinic=data['clinic'],
            date=data['date'],
            notes=data['notes'],
        )
        del request.session['appointment_data']
        messages.success(request, 'Rendez-vous confirmé ! Vous pouvez déposer vos documents.')
        # Redirige vers la page de dépôt de documents au lieu de la liste
        return redirect('appointment_documents', appointment_id=appointment.id)

    # Date affichée à l'heure locale (Europe/Paris)
    date_formatee = timezone.localtime(data['date']).strftime('%d/%m/%Y %H:%M')

    return render(request, 'appointments/confirm.html', {
        'specialist': data['specialist'],
        'exam_type': data['exam_type'],
        'clinic': data['clinic'],
        'date': date_formatee,
        'notes': data['notes'],
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
        # request.FILES contient les fichiers uploadés — différent de request.POST
        # Le formulaire valide côté serveur : extension, taille (5 Mo max), type de document
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.appointment = appointment
            # Sauvegarde le document en base et le fichier dans le stockage (R2 ou disque)
            document.save()
            messages.success(request, 'Document déposé avec succès !')
            # Recharge la page pour afficher le nouveau document
            return redirect('appointment_documents', appointment_id=appointment.id)
    else:
        form = DocumentUploadForm()

    return render(request, 'appointments/documents.html', {
        'appointment': appointment,
        # Formulaire de dépôt (avec ses éventuelles erreurs de validation)
        'form': form,
        # Choices pour le select du type de document
        'document_types': Document.DOCUMENT_TYPE_CHOICES,
        # Documents déjà déposés
        'documents': documents,
    })


def can_view_document(user, document):
    """Indique si l'utilisateur a le droit de consulter ce document médical.

    Autorisés : le patient du rendez-vous, le spécialiste du rendez-vous
    et les superutilisateurs (moindre privilège : is_staff ne suffit pas).
    """
    appointment = document.appointment
    return (
        user.is_superuser
        or appointment.patient_id == user.id
        or appointment.specialist.user_id == user.id
    )


@never_cache
@login_required
def document_download(request, document_id):
    """Ouvre un document médical après contrôle d'accès.

    Renvoie 404 si l'utilisateur n'a pas le droit de voir le document
    (sans révéler son existence) ou si le fichier n'existe plus.
    Avec R2 : redirection vers une URL signée valable 5 minutes.
    Avec le disque local : le fichier est servi directement par cette vue.
    """
    document = get_object_or_404(
        Document.objects.select_related('appointment__specialist'),  # pylint: disable=no-member
        pk=document_id,
    )
    if not can_view_document(request.user, document):
        raise Http404

    storage = document.file.storage
    if not storage.exists(document.file.name):
        raise Http404

    if isinstance(storage, FileSystemStorage):
        content_type, _ = mimetypes.guess_type(document.file.name)
        return FileResponse(
            document.file.open('rb'),
            as_attachment=content_type not in INLINE_CONTENT_TYPES,
            filename=os.path.basename(document.file.name),
        )

    # URL signée générée par django-storages (querystring_expire = 300 s)
    return redirect(document.file.url)


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

@login_required
def appointment_edit(request, appointment_id):
    """Vue de modification d'un rendez-vous (date et notes uniquement)."""
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user
    )

    # Impossible de modifier un rendez-vous annulé
    if appointment.status == 'cancelled':
        messages.error(request, 'Impossible de modifier un rendez-vous annulé.')
        return redirect('appointment_list')

    if request.method == 'POST':
        # Validation côté serveur : date obligatoire, format valide, date future
        form = AppointmentEditForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Rendez-vous modifié avec succès.')
            return redirect('appointment_list')
    else:
        form = AppointmentEditForm(instance=appointment)

    return render(request, 'appointments/edit.html', {
        'appointment': appointment,
        # Formulaire (avec ses éventuelles erreurs de validation)
        'form': form,
        'now': timezone.now().strftime('%Y-%m-%dT%H:%M'),
    })


import json

# Noms des champs dans l'API JSON (les formulaires utilisent les noms sans _id)
API_FIELD_NAMES = {'specialist': 'specialist_id', 'clinic': 'clinic_id', 'exam_type': 'exam_type_id'}


def parse_json_body(request):
    """Lit le corps JSON de la requête ; renvoie (données, None) ou (None, réponse 400)."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({'error': 'Corps de requête JSON invalide.'}, status=400)
    if not isinstance(data, dict):
        return None, JsonResponse(
            {'error': 'Le corps de la requête doit être un objet JSON.'}, status=400
        )
    return data, None


def api_validation_error(errors):
    """Réponse 400 avec le détail des erreurs par champ, noms de l'API."""
    return JsonResponse({
        'error': 'Données invalides.',
        'errors': {API_FIELD_NAMES.get(name, name): list(messages_) for name, messages_ in errors.items()},
    }, status=400)


@login_required
def api_appointments(request):
    """API CRUD — liste et création de rendez-vous (GET / POST)."""

    if request.method == 'GET':
        # Retourne les rendez-vous du patient connecté
        appointments = Appointment.objects.filter(  # pylint: disable=no-member
            patient=request.user
        ).values(
            'id', 'date', 'status', 'notes',
            'specialist__user__first_name', 'specialist__user__last_name',
            'specialist__specialty__name',
            'clinic__name', 'exam_type__name'
        ).order_by('-date')
        result = [
            {
                'id': a['id'],
                'date': a['date'].isoformat() if a['date'] else None,
                'status': a['status'],
                'notes': a['notes'],
                'specialist': f"Dr. {a['specialist__user__last_name']}",
                'specialty': a['specialist__specialty__name'],
                'clinic': a['clinic__name'],
                'exam_type': a['exam_type__name'],
            }
            for a in appointments
        ]
        return JsonResponse(result, safe=False)

    if request.method == 'POST':
        # Crée un nouveau rendez-vous — mêmes règles que le formulaire web
        data, error = parse_json_body(request)
        if error:
            return error
        form = AppointmentForm({
            'specialist': data.get('specialist_id'),
            'clinic': data.get('clinic_id'),
            'exam_type': data.get('exam_type_id'),
            'date': data.get('date'),
            'notes': data.get('notes', ''),
        })
        # Contrat de l'API conservé : clinique et type d'examen restent facultatifs
        form.fields['clinic'].required = False
        form.fields['exam_type'].required = False
        if not form.is_valid():
            return api_validation_error(form.errors)
        appointment = Appointment.objects.create(  # pylint: disable=no-member
            patient=request.user,
            **form.cleaned_data,
        )
        return JsonResponse({'id': appointment.id, 'status': 'created'}, status=201)

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@login_required
def api_appointment_detail(request, appointment_id):
    """API CRUD — détail, modification et suppression d'un rendez-vous (GET / PUT / DELETE)."""
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user
    )

    if request.method == 'GET':
        result = {
            'id': appointment.id,
            'date': appointment.date.isoformat() if appointment.date else None,
            'status': appointment.status,
            'notes': appointment.notes,
            'specialist': str(appointment.specialist),
            'clinic': appointment.clinic.name if appointment.clinic else None,
            'exam_type': appointment.exam_type.name if appointment.exam_type else None,
        }
        return JsonResponse(result)

    if request.method == 'PUT':
        # Modifie la date, les notes et/ou le statut — seuls les champs fournis sont validés
        data, error = parse_json_body(request)
        if error:
            return error
        errors = {}
        if 'date' in data:
            # Mêmes règles que le formulaire web : obligatoire, format valide, date future
            try:
                appointment.date = AppointmentDateField().clean(data['date'])
            except ValidationError as exc:
                errors['date'] = exc.messages
        if 'notes' in data:
            appointment.notes = forms.CharField(required=False).clean(data['notes'])
        if 'status' in data:
            if data['status'] in dict(Appointment.STATUS_CHOICES):
                appointment.status = data['status']
            else:
                errors['status'] = ['Statut invalide : valeurs possibles pending, confirmed, cancelled.']
        if errors:
            return api_validation_error(errors)
        appointment.save()
        return JsonResponse({'id': appointment.id, 'status': 'updated'})

    if request.method == 'DELETE':
        # Annule le rendez-vous (soft delete — on passe en cancelled)
        appointment.status = 'cancelled'
        appointment.save()
        return JsonResponse({'id': appointment.id, 'status': 'cancelled'})

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
