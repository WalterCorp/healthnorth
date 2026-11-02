"""Tests de l'application appointments — accès sécurisé aux documents médicaux."""

# pylint: disable=no-member
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import MAX_UPLOAD_SIZE
from .models import Appointment, Document, Specialist, Specialty

User = get_user_model()

# Dossier temporaire : les tests n'écrivent jamais dans media/ et ne contactent jamais R2
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='healthnorth-tests-')
TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


def tearDownModule():  # pylint: disable=invalid-name
    """Supprime le dossier temporaire une fois tous les tests du module terminés."""
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


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


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, STORAGES=TEST_STORAGES)
class DocumentUploadValidationTests(TestCase):
    """Validation côté serveur du dépôt de documents (extension, taille, type)."""

    @classmethod
    def setUpTestData(cls):
        """Crée un patient et un rendez-vous sur lequel déposer des documents."""
        specialty = Specialty.objects.create(name='Radiologie', duration_minutes=30)
        cls.patient = User.objects.create_user('upload_patient', password='pw-test-7')
        doctor = Specialist.objects.create(
            user=User.objects.create_user('upload_doctor', password='pw-test-8'),
            specialty=specialty,
        )
        cls.appointment = Appointment.objects.create(
            patient=cls.patient, specialist=doctor,
            date=timezone.now() + timedelta(days=7),
        )
        cls.url = reverse('appointment_documents', args=[cls.appointment.pk])

    def setUp(self):
        """Connecte le patient avant chaque test."""
        self.client.force_login(self.patient)

    def upload(self, name, content=b'%PDF-1.4 test', document_type='ordonnance'):
        """Envoie un fichier au formulaire de dépôt."""
        data = {'document_type': document_type}
        if name is not None:
            data['file'] = SimpleUploadedFile(name, content)
        return self.client.post(self.url, data)

    def assert_rejected(self, response, message):
        """Vérifie que le dépôt est refusé avec le message attendu, sans document créé."""
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, message)
        self.assertFalse(Document.objects.filter(appointment=self.appointment).exists())

    def test_valid_pdf_is_accepted(self):
        """Un PDF valide est enregistré et la page est rechargée."""
        response = self.upload('ordonnance.pdf')
        self.assertRedirects(response, self.url)
        document = Document.objects.get(appointment=self.appointment)
        self.assertEqual(document.document_type, 'ordonnance')

    def test_uppercase_extension_is_accepted(self):
        """L'extension est vérifiée sans tenir compte de la casse (.JPG)."""
        self.assertRedirects(self.upload('photo.JPG', b'\xff\xd8\xff'), self.url)

    def test_wrong_extension_is_rejected(self):
        """Un fichier .exe ou .html est refusé côté serveur, malgré l'attribut accept."""
        for name in ('virus.exe', 'page.html', 'document.pdf.exe', 'sans_extension'):
            with self.subTest(name=name):
                self.assert_rejected(self.upload(name), 'Format de fichier non autorisé')

    def test_file_too_large_is_rejected(self):
        """Un fichier de plus de 5 Mo est refusé."""
        response = self.upload('gros.pdf', b'0' * (MAX_UPLOAD_SIZE + 1))
        self.assert_rejected(response, 'taille maximale autorisée (5 Mo)')

    def test_file_at_size_limit_is_accepted(self):
        """Un fichier d'exactement 5 Mo est accepté."""
        self.assertRedirects(self.upload('limite.pdf', b'0' * MAX_UPLOAD_SIZE), self.url)

    def test_invalid_document_type_is_rejected(self):
        """Un type de document hors des choix autorisés est refusé."""
        self.assert_rejected(self.upload('ok.pdf', document_type='piratage'),
                             'Type de document invalide')

    def test_missing_file_is_rejected(self):
        """Le formulaire sans fichier affiche un message clair."""
        self.assert_rejected(self.upload(None), 'Veuillez sélectionner un fichier')

    def test_other_patient_cannot_upload(self):
        """Un autre patient ne peut pas déposer sur ce rendez-vous (404)."""
        other = User.objects.create_user('upload_other', password='pw-test-9')
        self.client.force_login(other)
        self.assertEqual(self.upload('ok.pdf').status_code, 404)

    def test_original_file_name_is_not_kept(self):
        """Le fichier reçoit un nom aléatoire (uuid) : le nom d'origine n'est jamais stocké."""
        self.upload('Ordonnance_Jean_Dupont_diabete.PDF')
        name = Document.objects.get(appointment=self.appointment).file.name
        self.assertRegex(name, r'^documents/[0-9a-f]{32}\.pdf$')
        self.assertNotIn('Dupont', name)

    def test_same_name_gives_distinct_files(self):
        """Deux dépôts du même nom produisent deux fichiers distincts."""
        self.upload('scan.pdf')
        self.upload('scan.pdf')
        names = set(Document.objects.filter(appointment=self.appointment)
                    .values_list('file', flat=True))
        self.assertEqual(len(names), 2)

    def test_documents_page_hides_file_name(self):
        """La page affiche « Ouvrir le document (PDF) » et jamais le nom stocké."""
        self.upload('Ordonnance_Jean_Dupont.pdf')
        document = Document.objects.get(appointment=self.appointment)
        page = self.client.get(self.url)
        self.assertContains(page, 'Ouvrir le document (PDF)')
        self.assertNotContains(page, document.file.name.split('/')[-1])
        self.assertNotContains(page, 'Dupont')
