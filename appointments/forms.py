"""Formulaires de l'application appointments."""

import os

from django import forms
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from .models import Appointment, Clinic, Document, ExamType, Specialist

# Extensions autorisées pour les documents médicaux
ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png']
# Taille maximale d'un document : 5 Mo
MAX_UPLOAD_SIZE = 5 * 1024 * 1024

# Signatures (premiers octets) attendues pour chaque extension
FILE_SIGNATURES = {
    'pdf': (b'%PDF-', 'PDF'),
    'png': (b'\x89PNG\r\n\x1a\n', 'PNG'),
    'jpg': (b'\xff\xd8\xff', 'JPEG'),
    'jpeg': (b'\xff\xd8\xff', 'JPEG'),
}


def file_matches_extension(file):
    """Vérifie que les premiers octets du fichier correspondent à son extension.

    Empêche par exemple un exécutable ou un texte renommé en .pdf.
    Le curseur du fichier est remis au début après la lecture.
    """
    extension = os.path.splitext(file.name)[1].lstrip('.').lower()
    signature, _ = FILE_SIGNATURES[extension]
    file.seek(0)
    header = file.read(len(signature))
    file.seek(0)
    return header == signature


class DocumentUploadForm(forms.ModelForm):
    """Formulaire de dépôt d'un document médical, validé côté serveur.

    L'attribut HTML accept ne suffit pas (il se contourne facilement) :
    l'extension, la taille et le type de document sont vérifiés ici.
    """

    class Meta:
        """Options du formulaire."""

        model = Document
        fields = ['document_type', 'file']
        error_messages = {
            'document_type': {
                'required': 'Veuillez choisir un type de document.',
                'invalid_choice': 'Type de document invalide.',
            },
            'file': {
                'required': 'Veuillez sélectionner un fichier.',
            },
        }

    def __init__(self, *args, **kwargs):
        """Ajoute la validation d'extension sur le champ fichier."""
        super().__init__(*args, **kwargs)
        self.fields['file'].validators.append(FileExtensionValidator(
            allowed_extensions=ALLOWED_EXTENSIONS,
            message='Format de fichier non autorisé : seuls les fichiers '
                    'PDF, JPG, JPEG et PNG sont acceptés.',
        ))

    def clean_file(self):
        """Refuse les fichiers de plus de 5 Mo ou dont le contenu ne correspond pas à l'extension.

        Appelée seulement si l'extension est autorisée (validateur du champ).
        """
        file = self.cleaned_data['file']
        if file.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                'Le fichier dépasse la taille maximale autorisée (5 Mo).'
            )
        if not file_matches_extension(file):
            extension = os.path.splitext(file.name)[1].lstrip('.').lower()
            raise forms.ValidationError(
                "Le contenu du fichier ne correspond pas à son extension : ce n'est pas "
                f"un vrai fichier {FILE_SIGNATURES[extension][1]}. Vérifiez le document "
                "et déposez l'original."
            )
        return file


# Messages d'erreur de la date d'un rendez-vous (formulaires web et API)
DATE_REQUIRED_MESSAGE = "Veuillez indiquer la date et l'heure du rendez-vous."
DATE_INVALID_MESSAGE = (
    "Date et heure invalides : format attendu AAAA-MM-JJTHH:MM (exemple : 2027-05-12T14:30)."
)
DATE_PAST_MESSAGE = "La date du rendez-vous doit être dans le futur."


class AppointmentDateField(forms.DateTimeField):
    """Date et heure d'un rendez-vous : obligatoire, format valide et dans le futur.

    Accepte le format du champ datetime-local (2027-05-12T14:30) et l'ISO 8601
    de l'API ; la date est interprétée dans le fuseau du site (Europe/Paris).
    """

    default_error_messages = {
        'required': DATE_REQUIRED_MESSAGE,
        'invalid': DATE_INVALID_MESSAGE,
    }

    def validate(self, value):
        """Refuse une date passée (le contrôle « min » du navigateur se contourne)."""
        super().validate(value)
        if value is not None and value <= timezone.now():
            raise forms.ValidationError(DATE_PAST_MESSAGE, code='past_date')


class AppointmentForm(forms.Form):
    """Prise de rendez-vous, validée côté serveur (formulaire web et API POST)."""

    clinic = forms.ModelChoiceField(
        queryset=Clinic.objects.all(),  # pylint: disable=no-member
        error_messages={
            'required': 'Veuillez choisir une clinique.',
            'invalid_choice': 'Clinique introuvable.',
        },
    )
    specialist = forms.ModelChoiceField(
        queryset=Specialist.objects.all(),  # pylint: disable=no-member
        error_messages={
            'required': 'Veuillez choisir un spécialiste.',
            'invalid_choice': 'Spécialiste introuvable.',
        },
    )
    exam_type = forms.ModelChoiceField(
        queryset=ExamType.objects.all(),  # pylint: disable=no-member
        error_messages={
            'required': "Veuillez choisir un type d'examen.",
            'invalid_choice': "Type d'examen introuvable.",
        },
    )
    date = AppointmentDateField()
    notes = forms.CharField(required=False)

    def session_data(self):
        """Données validées, sérialisables en session, pour l'écran de confirmation."""
        data = self.cleaned_data
        return {
            'clinic': data['clinic'].pk,
            'specialist': data['specialist'].pk,
            'exam_type': data['exam_type'].pk,
            'date': data['date'].isoformat(),
            'notes': data['notes'].strip(),
        }


class AppointmentEditForm(forms.ModelForm):
    """Modification d'un rendez-vous (date et notes), validée côté serveur."""

    class Meta:
        """Options du formulaire."""

        model = Appointment
        fields = ['date', 'notes']
        field_classes = {'date': AppointmentDateField}
