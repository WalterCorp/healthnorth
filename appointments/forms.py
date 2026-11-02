"""Formulaires de l'application appointments."""

from django import forms
from django.core.validators import FileExtensionValidator
from .models import Document

# Extensions autorisées pour les documents médicaux
ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png']
# Taille maximale d'un document : 5 Mo
MAX_UPLOAD_SIZE = 5 * 1024 * 1024


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
        """Refuse les fichiers de plus de 5 Mo."""
        file = self.cleaned_data['file']
        if file.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                'Le fichier dépasse la taille maximale autorisée (5 Mo).'
            )
        return file
