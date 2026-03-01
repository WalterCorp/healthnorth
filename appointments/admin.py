"""Configuration de l'administration pour l'application appointments."""

from django.contrib import admin
from .models import Specialty, Specialist, Appointment


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    """Administration des spécialités médicales."""

    list_display = ('name', 'duration_minutes')


@admin.register(Specialist)
class SpecialistAdmin(admin.ModelAdmin):
    """Administration des médecins spécialistes."""

    list_display = ('user', 'specialty')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Administration des rendez-vous médicaux."""

    list_display = ('patient', 'specialist', 'date', 'status')
    list_filter = ('status',)