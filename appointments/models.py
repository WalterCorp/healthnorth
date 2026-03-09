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


# Clinique / laboratoire Health North
class Clinic(models.Model):
    """Clinique ou laboratoire Health North sur le territoire français."""

    # Régions françaises disponibles
    REGION_CHOICES = [
        ('ile-de-france', 'Île-de-France'),
        ('auvergne-rhone-alpes', 'Auvergne-Rhône-Alpes'),
        ('nouvelle-aquitaine', 'Nouvelle-Aquitaine'),
        ('occitanie', 'Occitanie'),
        ('hauts-de-france', 'Hauts-de-France'),
        ('provence-alpes-cote-azur', "Provence-Alpes-Côte d'Azur"),
        ('grand-est', 'Grand Est'),
        ('pays-de-la-loire', 'Pays de la Loire'),
        ('normandie', 'Normandie'),
        ('bretagne', 'Bretagne'),
        ('bourgogne-franche-comte', 'Bourgogne-Franche-Comté'),
        ('centre-val-de-loire', 'Centre-Val de Loire'),
    ]

    name = models.CharField(max_length=200)
    # Région administrative française
    region = models.CharField(max_length=100, choices=REGION_CHOICES)
    # Département (ex: Paris, Rhône, Gironde)
    department = models.CharField(max_length=100)
    # Ville
    city = models.CharField(max_length=100)
    # Adresse complète
    address = models.CharField(max_length=255)
    # Téléphone
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        """Options du modèle Clinic."""
        verbose_name = "Clinique"
        verbose_name_plural = "Cliniques"
        # Tri par région puis par ville
        ordering = ['region', 'city', 'name']

    def __str__(self) -> str:
        """Retourne le nom et la ville de la clinique."""
        return str(f"{self.name} — {self.city}")


# Médecin spécialiste
class Specialist(models.Model):
    """Médecin spécialiste lié à un compte utilisateur."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialty = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, null=True
    )
    # Clinique(s) où exerce le spécialiste
    # ManyToMany : un spécialiste peut exercer dans plusieurs cliniques
    # et une clinique peut avoir plusieurs spécialistes
    clinics = models.ManyToManyField(Clinic, blank=True)
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

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmé'),
        ('cancelled', 'Annulé'),
    ]

    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='appointments'
    )
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE)
    exam_type = models.ForeignKey(
        ExamType, on_delete=models.SET_NULL, null=True, blank=True
    )
    # Clinique choisie pour le rendez-vous — SET_NULL si la clinique est supprimée
    clinic = models.ForeignKey(
        Clinic, on_delete=models.SET_NULL, null=True, blank=True
    )
    date = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    notes = models.TextField(blank=True)

    class Meta:
        """Options du modèle Appointment."""
        verbose_name = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"

    def __str__(self) -> str:
        """Retourne une représentation du rendez-vous."""
        return str(f"{self.patient} - {self.specialist} - {self.date}")