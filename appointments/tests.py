"""Tests de l'application appointments — accès sécurisé aux documents médicaux."""

# pylint: disable=no-member
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Appointment, Document, Specialist, Specialty

User = get_user_model()

# Dossier temporaire : les tests n'écrivent jamais dans media/ et ne contactent jamais R2
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='healthnorth-tests-')
TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, STORAGES=TEST_STORAGES)
class DocumentDownloadTests(TestCase):
    """Contrôle d'accès de la vue document_download."""

    @classmethod
    def setUpTestData(cls):
        """Crée un rendez-vous avec un document, et des utilisateurs autorisés ou non."""
        specialty = Specialty.objects.create(name='Cardiologie', duration_minutes=30)
        cls.patient = User.objects.create_user('patient', password='pw-test-1')
        cls.other_patient = User.objects.create_user('other', password='pw-test-2')
        cls.doctor_user = User.objects.create_user('doctor', password='pw-test-3')
        cls.other_doctor_user = User.objects.create_user('other_doctor', password='pw-test-4')
        cls.staff_user = User.objects.create_user('staff', password='pw-test-5', is_staff=True)
        cls.superuser = User.objects.create_superuser('root', password='pw-test-6')
        doctor = Specialist.objects.create(user=cls.doctor_user, specialty=specialty)
        Specialist.objects.create(user=cls.other_doctor_user, specialty=specialty)

        appointment = Appointment.objects.create(
            patient=cls.patient, specialist=doctor,
            date=timezone.now() + timedelta(days=7),
        )
        cls.document = Document(appointment=appointment, document_type='ordonnance')
        cls.document.file.save('ordonnance.pdf', ContentFile(b'%PDF-1.4 test'), save=True)
        cls.url = reverse('document_download', args=[cls.document.pk])

    @classmethod
    def tearDownClass(cls):
        """Supprime le dossier temporaire des fichiers uploadés."""
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def get_as(self, user):
        """Ouvre le document en étant connecté avec l'utilisateur donné."""
        self.client.force_login(user)
        return self.client.get(self.url)

    def test_anonymous_redirected_to_login(self):
        """Un visiteur non connecté est redirigé vers la page de connexion."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('login')))

    def test_patient_can_view_own_document(self):
        """Le patient du rendez-vous voit son document, affiché dans le navigateur."""
        response = self.get_as(self.patient)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 test')
        self.assertTrue(response['Content-Disposition'].startswith('inline'))
        self.assertIn('no-store', response['Cache-Control'])

    def test_specialist_of_appointment_can_view(self):
        """Le spécialiste du rendez-vous voit le document."""
        self.assertEqual(self.get_as(self.doctor_user).status_code, 200)

    def test_superuser_can_view(self):
        """Un superutilisateur voit le document."""
        self.assertEqual(self.get_as(self.superuser).status_code, 200)

    def test_other_patient_gets_404(self):
        """Un autre patient reçoit 404, sans savoir que le document existe."""
        self.assertEqual(self.get_as(self.other_patient).status_code, 404)

    def test_other_specialist_gets_404(self):
        """Un spécialiste étranger au rendez-vous reçoit 404."""
        self.assertEqual(self.get_as(self.other_doctor_user).status_code, 404)

    def test_staff_without_superuser_gets_404(self):
        """is_staff ne suffit pas : moindre privilège."""
        self.assertEqual(self.get_as(self.staff_user).status_code, 404)

    def test_unknown_document_gets_404(self):
        """Un identifiant inexistant renvoie 404."""
        self.client.force_login(self.patient)
        response = self.client.get(reverse('document_download', args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_missing_file_gets_404(self):
        """Une ligne Document dont le fichier a disparu renvoie 404."""
        missing = Document.objects.create(
            appointment=self.document.appointment, file='documents/disparu.pdf'
        )
        self.client.force_login(self.patient)
        response = self.client.get(reverse('document_download', args=[missing.pk]))
        self.assertEqual(response.status_code, 404)

    def test_non_inline_type_is_downloaded(self):
        """Un type non prévu (ex. HTML) est téléchargé, jamais affiché sur le domaine."""
        html = Document(appointment=self.document.appointment)
        html.file.save('page.html', ContentFile(b'<script>alert(1)</script>'), save=True)
        self.client.force_login(self.patient)
        response = self.client.get(reverse('document_download', args=[html.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Disposition'].startswith('attachment'))

    def test_media_url_not_served(self):
        """L'ancienne route /media/ n'existe plus : aucun accès direct au fichier."""
        self.client.force_login(self.patient)
        response = self.client.get('/media/' + self.document.file.name)
        self.assertEqual(response.status_code, 404)

    def test_documents_page_links_to_secure_view(self):
        """La page de dépôt pointe vers la vue sécurisée, pas vers file.url."""
        self.client.force_login(self.patient)
        page = self.client.get(
            reverse('appointment_documents', args=[self.document.appointment.pk])
        )
        self.assertContains(page, f'href="{self.url}"')
        self.assertNotContains(page, '/media/')
