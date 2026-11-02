"""Formulaires de l'application appointments."""

import os

from django import forms
from django.core.validators import FileExtensionValidator
from .models import Document

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
