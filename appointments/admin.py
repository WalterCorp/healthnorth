"""Configuration de l'administration pour l'application appointments."""

from django.contrib import admin
from .models import Specialty, Specialist, Appointment


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

    list_display = ('get_patient', 'get_specialist', 'date', 'get_status')
    list_filter = ('status',)

    @admin.display(description='Patient')
    def get_patient(self, obj):
        """Retourne le nom du patient."""
        return obj.patient

    @admin.display(description='Spécialiste')
    def get_specialist(self, obj):
        """Retourne le nom du spécialiste."""
        return obj.specialist

    @admin.display(description='Statut')
    def get_status(self, obj):
        """Retourne le statut lisible du rendez-vous."""
        return obj.get_status_display()