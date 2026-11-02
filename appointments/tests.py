"""Tests de l'application appointments — accès sécurisé aux documents médicaux."""

# pylint: disable=no-member
import io
import shutil
import tempfile
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .forms import MAX_UPLOAD_SIZE
from .models import Appointment, Document, Specialist, Specialty

User = get_user_model()

# Dossier temporaire : les tests n'écrivent jamais dans media/ et ne contactent jamais R2
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='healthnorth-tests-')
TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


def padded_pdf(size):
    """Contenu PDF valide (signature %PDF-) complété jusqu'à la taille demandée."""
    header = b'%PDF-1.4\n'
    return header + b'0' * (size - len(header))


def image_bytes(image_format):
    """Génère une vraie petite image (PNG ou JPEG) avec Pillow."""
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), 'white').save(buffer, format=image_format)
    return buffer.getvalue()


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
        response = self.upload('gros.pdf', padded_pdf(MAX_UPLOAD_SIZE + 1))
        self.assert_rejected(response, 'taille maximale autorisée (5 Mo)')

    def test_file_at_size_limit_is_accepted(self):
        """Un fichier d'exactement 5 Mo est accepté."""
        self.assertRedirects(self.upload('limite.pdf', padded_pdf(MAX_UPLOAD_SIZE)), self.url)

    def test_invalid_document_type_is_rejected(self):
        """Un type de document hors des choix autorisés est refusé."""
        self.assert_rejected(self.upload('ok.pdf', document_type='piratage'),
                             'Type de document invalide')

    def test_missing_file_is_rejected(self):
        """Le formulaire sans fichier affiche un message clair."""
        self.assert_rejected(self.upload(None), 'Veuillez sélectionner un fichier')

    def test_real_files_are_accepted(self):
        """Un vrai PDF, un vrai PNG et un vrai JPEG (.jpg et .jpeg) sont acceptés."""
        files = {
            'vrai.pdf': b'%PDF-1.7\n1 0 obj\n<< >>\nendobj\ntrailer\n<< >>\n%%EOF\n',
            'vrai.png': image_bytes('PNG'),
            'vrai.jpg': image_bytes('JPEG'),
            'vrai.jpeg': image_bytes('JPEG'),
        }
        for name, content in files.items():
            with self.subTest(name=name):
                self.assertRedirects(self.upload(name, content), self.url)
        self.assertEqual(Document.objects.filter(appointment=self.appointment).count(), 4)

    def test_fake_files_are_rejected(self):
        """Un contenu qui ne correspond pas à l'extension est refusé avec un message clair."""
        fakes = {
            'texte.pdf': (b'Ceci est un simple fichier texte', 'PDF'),
            'programme.pdf': (b'MZ\x90\x00\x03\x00\x00\x00', 'PDF'),
            'script.pdf': (b'#!/bin/sh\nrm -rf /\n', 'PDF'),
            'image_png.jpg': (image_bytes('PNG'), 'JPEG'),
            'pdf_renomme.png': (b'%PDF-1.4\n', 'PNG'),
        }
        for name, (content, label) in fakes.items():
            with self.subTest(name=name):
                self.assert_rejected(
                    self.upload(name, content),
                    f"ce n&#x27;est pas un vrai fichier {label}",
                )

    def test_empty_file_is_rejected(self):
        """Un fichier vide est refusé par Django avant même la vérification de signature."""
        self.assert_rejected(self.upload('vide.pdf', b''), 'est vide')

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


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, STORAGES=TEST_STORAGES)
class DocumentAdminTests(TestCase):
    """Administration des documents : superutilisateurs uniquement, lien sécurisé."""

    @classmethod
    def setUpTestData(cls):
        """Crée un document, un superutilisateur et un membre du staff avec toutes les permissions."""
        from django.contrib.auth.models import Permission  # pylint: disable=import-outside-toplevel
        specialty = Specialty.objects.create(name='Dermatologie', duration_minutes=30)
        patient = User.objects.create_user('admin_patient', password='pw-test-10')
        doctor = Specialist.objects.create(
            user=User.objects.create_user('admin_doctor', password='pw-test-11'),
            specialty=specialty,
        )
        appointment = Appointment.objects.create(
            patient=patient, specialist=doctor, date=timezone.now() + timedelta(days=7),
        )
        cls.document = Document(appointment=appointment, document_type='analyse')
        cls.document.file.save('Resultats_Dupont.pdf', ContentFile(b'%PDF-1.4'), save=True)
        cls.superuser = User.objects.create_superuser('admin_root', password='pw-test-12')
        cls.staff = User.objects.create_user('admin_staff', password='pw-test-13', is_staff=True)
        cls.staff.user_permissions.set(Permission.objects.filter(codename__endswith='_document'))
        cls.changelist = reverse('admin:appointments_document_changelist')
        cls.change = reverse('admin:appointments_document_change', args=[cls.document.pk])
        cls.secure_url = reverse('document_download', args=[cls.document.pk])

    def test_changelist_shows_secure_link(self):
        """La liste affiche patient, type et un lien vers la vue sécurisée."""
        self.client.force_login(self.superuser)
        page = self.client.get(self.changelist)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, f'href="{self.secure_url}"')
        self.assertContains(page, 'admin_patient')
        self.assertContains(page, "Résultats d&#x27;analyse")
        self.assertNotContains(page, self.document.file.name)

    def test_change_page_never_exposes_file_url(self):
        """La fiche n'affiche pas le widget fichier (lien file.url) mais le lien sécurisé."""
        self.client.force_login(self.superuser)
        page = self.client.get(self.change)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, f'href="{self.secure_url}"')
        self.assertNotContains(page, self.document.file.url)
        self.assertNotContains(page, 'type="file"')

    def test_add_is_disabled(self):
        """Aucun ajout possible depuis l'admin, même pour un superutilisateur."""
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse('admin:appointments_document_add')).status_code, 403)

    def test_staff_without_superuser_has_no_access(self):
        """is_staff avec toutes les permissions Document ne suffit pas : moindre privilège."""
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.changelist).status_code, 403)
        self.assertEqual(self.client.get(self.change).status_code, 403)
        self.assertNotContains(self.client.get(reverse('admin:index')), 'Documents')


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, STORAGES=TEST_STORAGES)
class DocumentFileDeletionTests(TestCase):
    """Suppression du fichier stocké quand un Document est supprimé (signal post_delete)."""

    @classmethod
    def setUpTestData(cls):
        """Crée un patient, un spécialiste et une spécialité réutilisés par les tests."""
        cls.specialty = Specialty.objects.create(name='Pédiatrie', duration_minutes=30)
        cls.patient = User.objects.create_user('delete_patient', password='pw-test-14')
        cls.doctor = Specialist.objects.create(
            user=User.objects.create_user('delete_doctor', password='pw-test-15'),
            specialty=cls.specialty,
        )

    def make_document(self):
        """Crée un rendez-vous avec un document, et renvoie (rendez-vous, document)."""
        appointment = Appointment.objects.create(
            patient=self.patient, specialist=self.doctor,
            date=timezone.now() + timedelta(days=7),
        )
        document = Document(appointment=appointment, document_type='ordonnance')
        document.file.save('a_supprimer.pdf', ContentFile(b'%PDF-1.4'), save=True)
        self.assertTrue(document.file.storage.exists(document.file.name))
        return appointment, document

    def test_direct_delete_removes_file(self):
        """document.delete() supprime aussi le fichier, après le commit."""
        _, document = self.make_document()
        storage, name = document.file.storage, document.file.name
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            document.delete()
            # Avant le commit, le fichier est toujours là
            self.assertTrue(storage.exists(name))
        self.assertEqual(len(callbacks), 1)
        self.assertFalse(storage.exists(name))

    def test_cascade_delete_from_appointment_removes_file(self):
        """Supprimer le rendez-vous supprime ses documents et leurs fichiers."""
        appointment, document = self.make_document()
        storage, name, pk = document.file.storage, document.file.name, document.pk
        with self.captureOnCommitCallbacks(execute=True):
            appointment.delete()
        self.assertFalse(Document.objects.filter(pk=pk).exists())
        self.assertFalse(storage.exists(name))

    def test_queryset_delete_removes_files(self):
        """Une suppression en masse (queryset, action de l'admin) supprime chaque fichier."""
        _, first = self.make_document()
        _, second = self.make_document()
        names = [first.file.name, second.file.name]
        with self.captureOnCommitCallbacks(execute=True):
            Document.objects.filter(pk__in=[first.pk, second.pk]).delete()
        for name in names:
            self.assertFalse(first.file.storage.exists(name))

    def test_rolled_back_delete_keeps_file(self):
        """Si la transaction est annulée, le document et son fichier sont conservés."""
        _, document = self.make_document()
        storage, name, pk = document.file.storage, document.file.name, document.pk
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    document.delete()
                    raise RuntimeError('annulation simulée')
        self.assertEqual(len(callbacks), 0)
        # delete() remet document.pk à None : on vérifie avec l'identifiant mémorisé
        self.assertTrue(Document.objects.filter(pk=pk).exists())
        self.assertTrue(storage.exists(name))

    def test_storage_error_is_logged_not_raised(self):
        """Une erreur du stockage est journalisée et ne fait pas planter la suppression."""
        _, document = self.make_document()
        pk = document.pk
        # default_storage est un objet paresseux : on simule l'erreur sur la classe réelle
        with mock.patch('django.core.files.storage.FileSystemStorage.delete',
                        side_effect=OSError('R2 indisponible')):
            with self.assertLogs('appointments.signals', level='ERROR') as logs:
                with self.captureOnCommitCallbacks(execute=True):
                    document.delete()
        self.assertIn('Impossible de supprimer le fichier', logs.output[0])
        self.assertFalse(Document.objects.filter(pk=pk).exists())


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, STORAGES=TEST_STORAGES)
class LocalTimezoneDisplayTests(TestCase):
    """Les heures de rendez-vous s'affichent à l'heure de Paris, pas en UTC."""

    @classmethod
    def setUpTestData(cls):
        """Crée un rendez-vous en hiver (UTC+1) et un en été (UTC+2), avec un document."""
        specialty = Specialty.objects.create(name='Cardiologie', duration_minutes=30)
        patient = User.objects.create_user('tz_patient', password='pw-test-16',
                                           first_name='Jean', last_name='Dupont')
        doctor = Specialist.objects.create(
            user=User.objects.create_user('tz_doctor', password='pw-test-17'),
            specialty=specialty,
        )
        # 11:00 UTC en mars = 12:00 à Paris ; 10:00 UTC en juillet = 12:00 à Paris
        cls.winter = Appointment.objects.create(
            patient=patient, specialist=doctor,
            date=datetime(2027, 3, 12, 11, 0, tzinfo=dt_timezone.utc),
        )
        cls.summer = Appointment.objects.create(
            patient=patient, specialist=doctor,
            date=datetime(2027, 7, 1, 10, 0, tzinfo=dt_timezone.utc),
        )
        document = Document(appointment=cls.winter, document_type='ordonnance')
        document.file.save('ordonnance.pdf', ContentFile(b'%PDF-1.4'), save=True)
        cls.superuser = User.objects.create_superuser('tz_root', password='pw-test-18')

    def test_str_uses_paris_time(self):
        """__str__ affiche 12:00 (heure de Paris) en hiver comme en été."""
        self.assertIn('12/03/2027 12:00', str(self.winter))
        self.assertIn('01/07/2027 12:00', str(self.summer))
        self.assertNotIn('11:00', str(self.winter))
        self.assertNotIn('+00:00', str(self.winter))

    def test_document_admin_uses_paris_time(self):
        """La colonne Rendez-vous de l'admin des documents est à l'heure de Paris."""
        self.client.force_login(self.superuser)
        page = self.client.get(reverse('admin:appointments_document_changelist'))
        self.assertContains(page, '12/03/2027 12:00')
        self.assertNotContains(page, '12/03/2027 11:00')

    def test_appointment_admin_uses_paris_time(self):
        """La liste des rendez-vous de l'admin affiche aussi 12:00."""
        self.client.force_login(self.superuser)
        page = self.client.get(reverse('admin:appointments_appointment_changelist'))
        self.assertContains(page, '12:00')
        self.assertNotContains(page, '11:00')
        self.assertNotContains(page, '10:00')
