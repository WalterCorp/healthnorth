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
    region = models.CharField(max_length=100, choices=REGION_CHOICES)
    department = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        """Options du modèle Clinic."""
        verbose_name = "Clinique"
        verbose_name_plural = "Cliniques"
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


# Document médical lié à un rendez-vous
class Document(models.Model):
    """Document médical déposé par le patient lors de la prise de rendez-vous.

    Exemples : ordonnance, certificat médical, résultats d'analyse.
    Les fichiers sont stockés dans le dossier media/documents/.
    """

    # Types de documents acceptés
    DOCUMENT_TYPE_CHOICES = [
        ('ordonnance', 'Ordonnance'),
        ('certificat', 'Certificat médical'),
        ('analyse', "Résultats d'analyse"),
        ('autre', 'Autre'),
    ]

    # Rendez-vous auquel est lié le document
    # CASCADE : si le RDV est supprimé, les documents le sont aussi
    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name='documents'
    )
    # Type de document pour faciliter le tri et l'affichage
    document_type = models.CharField(
        max_length=50, choices=DOCUMENT_TYPE_CHOICES, default='autre'
    )
    # Fichier uploadé — stocké dans media/documents/
    # upload_to : sous-dossier dans MEDIA_ROOT
    file = models.FileField(upload_to='documents/')
    # Date d'upload — auto_now_add : rempli automatiquement à la création
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Options du modèle Document."""
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self) -> str:
        """Retourne le type de document et le rendez-vous associé."""
        return str(f"{self.get_document_type_display()} — {self.appointment}")  # pylint: disable=no-member