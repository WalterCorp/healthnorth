"""Configuration de l'administration pour l'application appointments."""

from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from .models import Specialty, Specialist, Appointment, ExamType, Clinic, Document


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    """Administration des spécialités médicales."""

    list_display = ('get_name', 'get_duration')

    @admin.display(description='Nom')
    def get_name(self, obj):
        """Retourne le nom de la spécialité."""
        return obj.name

    @admin.display(description='Durée (minutes)')
    def get_duration(self, obj):
        """Retourne la durée moyenne d'un rendez-vous."""
        return obj.duration_minutes


@admin.register(ExamType)
class ExamTypeAdmin(admin.ModelAdmin):
    """Administration des types d'examens médicaux."""

    list_display = ('get_name', 'get_duration', 'get_specialty')

    @admin.display(description="Nom de l'examen")
    def get_name(self, obj):
        """Retourne le nom de l'examen."""
        return obj.name

    @admin.display(description='Durée (minutes)')
    def get_duration(self, obj):
        """Retourne la durée estimée de l'examen."""
        return obj.duration_minutes

    @admin.display(description='Spécialité associée')
    def get_specialty(self, obj):
        """Retourne la spécialité associée à l'examen."""
        return obj.specialty


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    """Administration des cliniques et laboratoires Health North."""

    # Colonnes affichées dans la liste des cliniques
    list_display = ('get_name', 'get_region', 'get_department', 'get_city')
    # Filtre latéral par région pour faciliter la navigation
    list_filter = ('region',)

    @admin.display(description='Nom')
    def get_name(self, obj):
        """Retourne le nom de la clinique."""
        return obj.name

    @admin.display(description='Région')
    def get_region(self, obj):
        """Retourne le label lisible de la région (ex: Île-de-France)."""
        # get_region_display() utilise les REGION_CHOICES du modèle
        return obj.get_region_display()

    @admin.display(description='Département')
    def get_department(self, obj):
        """Retourne le département de la clinique."""
        return obj.department

    @admin.display(description='Ville')
    def get_city(self, obj):
        """Retourne la ville de la clinique."""
        return obj.city


@admin.register(Specialist)
class SpecialistAdmin(admin.ModelAdmin):
    """Administration des médecins spécialistes."""

    list_display = ('get_user', 'get_specialty')

    @admin.display(description='Utilisateur')
    def get_user(self, obj):
        """Retourne le nom de l'utilisateur lié au spécialiste."""
        return obj.user

    @admin.display(description='Spécialité')
    def get_specialty(self, obj):
        """Retourne la spécialité du médecin."""
        return obj.specialty


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Administration des rendez-vous médicaux."""

    # Colonnes affichées dans la liste des rendez-vous
    list_display = ('get_patient', 'get_specialist', 'get_exam_type', 'get_clinic', 'date', 'get_status')
    # Filtre latéral par statut
    list_filter = ('status',)

    @admin.display(description='Patient')
    def get_patient(self, obj):
        """Retourne le nom du patient."""
        return obj.patient

    @admin.display(description='Spécialiste')
    def get_specialist(self, obj):
        """Retourne le nom du spécialiste."""
        return obj.specialist

    @admin.display(description="Type d'examen")
    def get_exam_type(self, obj):
        """Retourne le type d'examen — tiret si non renseigné."""
        return obj.exam_type if obj.exam_type else '—'

    @admin.display(description='Clinique')
    def get_clinic(self, obj):
        """Retourne la clinique du rendez-vous — tiret si non renseignée."""
        return obj.clinic if obj.clinic else '—'

    @admin.display(description='Statut')
    def get_status(self, obj):
        """Retourne le statut lisible du rendez-vous."""
        return obj.get_status_display()

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Administration des documents médicaux.

    Données de santé : module réservé aux superutilisateurs (moindre privilège),
    et le fichier n'est jamais exposé via file.url — le lien passe par la vue
    sécurisée document_download (contrôle d'accès puis URL signée).
    """

    # Colonnes affichées dans la liste des documents
    list_display = ('get_patient', 'get_appointment', 'get_document_type', 'get_uploaded_at', 'get_file_link')
    # Filtre latéral par type de document
    list_filter = ('document_type',)
    # Évite une requête par ligne pour le patient et le spécialiste
    list_select_related = ('appointment__patient', 'appointment__specialist__user')
    # Seul le type de document est modifiable : le fichier n'est jamais remplacé ici
    fields = ('appointment', 'document_type', 'get_file_link', 'uploaded_at')
    readonly_fields = ('appointment', 'get_file_link', 'uploaded_at')

    @admin.display(description='Patient')
    def get_patient(self, obj):
        """Retourne le patient : « Prénom Nom (identifiant) », ou l'identifiant seul si le nom est vide."""
        patient = obj.appointment.patient
        full_name = patient.get_full_name()
        return f"{full_name} ({patient.username})" if full_name else patient.username

    @admin.display(description='Rendez-vous')
    def get_appointment(self, obj):
        """Retourne la date (heure locale Europe/Paris) et le spécialiste du rendez-vous."""
        local_date = timezone.localtime(obj.appointment.date)
        return f"{local_date:%d/%m/%Y %H:%M} — {obj.appointment.specialist}"

    @admin.display(description='Type')
    def get_document_type(self, obj):
        """Retourne le type de document lisible (ex: Ordonnance)."""
        return obj.get_document_type_display()

    @admin.display(description='Déposé le', ordering='uploaded_at')
    def get_uploaded_at(self, obj):
        """Retourne la date de dépôt du document."""
        return obj.uploaded_at

    @admin.display(description='Fichier')
    def get_file_link(self, obj):
        """Lien vers la vue sécurisée — jamais vers file.url."""
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Ouvrir le document ({})</a>',
            reverse('document_download', args=[obj.pk]),
            obj.file_extension,
        )

    def has_module_permission(self, request):
        """Module visible uniquement par les superutilisateurs."""
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        """Consultation réservée aux superutilisateurs."""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Modification (type de document uniquement) réservée aux superutilisateurs."""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Suppression réservée aux superutilisateurs."""
        return request.user.is_superuser

    def has_add_permission(self, request):
        """Pas d'ajout depuis l'admin : les dépôts passent par le formulaire validé."""
        return False
