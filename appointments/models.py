"""Modèles de l'application appointments — gestion des rendez-vous médicaux."""

from django.db import models
from accounts.models import User


# Spécialité médicale (ex: cardiologie, radiologie)
class Specialty(models.Model):
    """Spécialité médicale proposée par les praticiens."""

    name = models.CharField(max_length=100)
    # Durée moyenne d'un rendez-vous pour cette spécialité
    duration_minutes = models.IntegerField(default=30)

    # Métadonnées du modèle
    class Meta:
        """Options du modèle Specialty."""
        verbose_name = "Spécialité"
        verbose_name_plural = "Spécialités"

    def __str__(self) -> str:
        """Retourne le nom de la spécialité."""
        return str(self.name)


# Médecin spécialiste
class Specialist(models.Model):
    """Médecin spécialiste lié à un compte utilisateur."""

    # Lien vers le compte utilisateur du spécialiste
    # OneToOne = un spécialiste = un seul compte utilisateur
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Spécialité du médecin — SET_NULL si la spécialité est supprimée
    specialty = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, null=True
    )
    bio = models.TextField(blank=True)

    def __str__(self) -> str:
        """Retourne le nom du spécialiste."""
        return str(f"Dr. {self.user.last_name}")  # pylint: disable=no-member


# Rendez-vous médical
class Appointment(models.Model):
    """Rendez-vous médical entre un patient et un spécialiste."""

    # Statuts possibles d'un rendez-vous
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmé'),
        ('cancelled', 'Annulé'),
    ]

    # Patient qui prend le rendez-vous
    # related_name permet d'accéder aux RDV d'un patient via patient.appointments.all()
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='appointments'
    )
    # Spécialiste concerné
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE)
    # Date et heure du rendez-vous
    date = models.DateTimeField()
    # Statut actuel du rendez-vous
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    # Notes médicales optionnelles
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        """Retourne une représentation du rendez-vous."""
        return str(f"{self.patient} - {self.specialist} - {self.date}")