"""Modèles de l'application appointments — gestion des rendez-vous médicaux."""

from django.db import models
from accounts.models import User


# Spécialité médicale (ex: cardiologie, radiologie)
class Specialty(models.Model):
    """Spécialité médicale proposée par les praticiens."""

    name = models.CharField(max_length=100)
    # Durée moyenne d'un rendez-vous pour cette spécialité
    duration_minutes = models.IntegerField(default=30)

    class Meta:
        """Options du modèle Specialty."""
        verbose_name = "Spécialité"
        verbose_name_plural = "Spécialités"

    def __str__(self) -> str:
        """Retourne le nom de la spécialité."""
        return str(self.name)


# Type d'examen médical (ex: prise de sang, IRM, scanner)
class ExamType(models.Model):
    """Type d'examen médical disponible dans les cliniques Health North."""

    name = models.CharField(max_length=200)
    # Durée estimée de l'examen en minutes
    duration_minutes = models.IntegerField(default=30)
    # Description optionnelle de l'examen
    description = models.TextField(blank=True)
    # Spécialité médicale associée à cet examen
    # SET_NULL : si la spécialité est supprimée, l'examen reste mais sans spécialité
    specialty = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        """Options du modèle ExamType."""
        verbose_name = "Type d'examen"
        verbose_name_plural = "Types d'examens"

    def __str__(self) -> str:
        """Retourne le nom de l'examen et sa durée."""
        return str(f"{self.name} ({self.duration_minutes} min)")


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

    class Meta:
        """Options du modèle Specialist."""
        verbose_name = "Spécialiste"
        verbose_name_plural = "Spécialistes"

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
    # Type d'examen choisi — SET_NULL si le type est supprimé
    exam_type = models.ForeignKey(
        ExamType, on_delete=models.SET_NULL, null=True, blank=True
    )
    # Date et heure du rendez-vous
    date = models.DateTimeField()
    # Statut actuel du rendez-vous
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    # Notes médicales optionnelles
    notes = models.TextField(blank=True)

    class Meta:
        """Options du modèle Appointment."""
        verbose_name = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"

    def __str__(self) -> str:
        """Retourne une représentation du rendez-vous."""
        return str(f"{self.patient} - {self.specialist} - {self.date}")