"""Commande Django pour peupler la base de données en production."""

# pylint: disable=no-member
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from appointments.models import Specialist, Specialty, Clinic

User = get_user_model()


class Command(BaseCommand):
    """Crée les utilisateurs de test et associe les cliniques aux spécialistes."""

    help = "Peuple la base de données avec les données de test"

    def handle(self, *args, **options):
        """Exécute le script de peuplement."""

        # Superuser admin
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@healthnorth.com', 'admin1234')
            self.stdout.write('Admin créé')

        # Patient de test
        if not User.objects.filter(username='patient1').exists():
            u = User.objects.create_user('patient1', 'patient1@healthnorth.com', 'NewPass456!')
            u.first_name = 'Jean'
            u.last_name = 'Dupont'
            u.save()
            self.stdout.write('Patient1 créé')

        # Dr. Martin — Cardiologue
        if not User.objects.filter(username='dr.martin').exists():
            u = User.objects.create_user('dr.martin', 'martin@healthnorth.com', 'TestPass123!')
            u.first_name = 'Pierre'
            u.last_name = 'Martin'
            u.save()
            Specialist.objects.create(user=u, specialty=Specialty.objects.get(pk=1))
            self.stdout.write('Dr. Martin créé')
        elif not Specialist.objects.filter(user__username='dr.martin').exists():
            u = User.objects.get(username='dr.martin')
            Specialist.objects.create(user=u, specialty=Specialty.objects.get(pk=1))
            self.stdout.write('Specialist Martin créé')

        # Dr. Dubois — Radiologue
        if not User.objects.filter(username='dr.dubois').exists():
            u = User.objects.create_user('dr.dubois', 'dubois@healthnorth.com', 'TestPass123!')
            u.first_name = 'Sophie'
            u.last_name = 'Dubois'
            u.save()
            Specialist.objects.create(user=u, specialty=Specialty.objects.get(pk=2))
            self.stdout.write('Dr. Dubois créé')
        elif not Specialist.objects.filter(user__username='dr.dubois').exists():
            u = User.objects.get(username='dr.dubois')
            Specialist.objects.create(user=u, specialty=Specialty.objects.get(pk=2))
            self.stdout.write('Specialist Dubois créé')

        # Dr. Bernard — Dermatologue
        if not User.objects.filter(username='dr.bernard').exists():
            u = User.objects.create_user('dr.bernard', 'bernard@healthnorth.com', 'TestPass123!')
            u.first_name = 'Claire'
            u.last_name = 'Bernard'
            u.save()
            Specialist.objects.create(user=u, specialty=Specialty.objects.get(pk=3))
            self.stdout.write('Dr. Bernard créé')
        elif not Specialist.objects.filter(user__username='dr.bernard').exists():
            u = User.objects.get(username='dr.bernard')
            Specialist.objects.create(user=u, specialty=Specialty.objects.get(pk=3))
            self.stdout.write('Specialist Bernard créé')

        # Dr. Leroy — Pédiatre
        if not User.objects.filter(username='dr.leroy').exists():
            u = User.objects.create_user('dr.leroy', 'leroy@healthnorth.com', 'TestPass123!')
            u.first_name = 'Marc'
            u.last_name = 'Leroy'
            u.save()
            Specialist.objects.create(user=u, specialty=Specialty.objects.get(pk=4))
            self.stdout.write('Dr. Leroy créé')
        elif not Specialist.objects.filter(user__username='dr.leroy').exists():
            u = User.objects.get(username='dr.leroy')
            Specialist.objects.create(user=u, specialty=Specialty.objects.get(pk=4))
            self.stdout.write('Specialist Leroy créé')

        # Association cliniques — spécialistes
        martin = Specialist.objects.get(user__username='dr.martin')
        dubois = Specialist.objects.get(user__username='dr.dubois')
        bernard = Specialist.objects.get(user__username='dr.bernard')
        leroy = Specialist.objects.get(user__username='dr.leroy')

        Clinic.objects.get(pk=1).specialist_set.set([martin, dubois])
        Clinic.objects.get(pk=2).specialist_set.set([martin, bernard])
        Clinic.objects.get(pk=3).specialist_set.set([dubois, leroy])
        Clinic.objects.get(pk=4).specialist_set.set([bernard, leroy])
        Clinic.objects.get(pk=5).specialist_set.set([martin, leroy])
        Clinic.objects.get(pk=6).specialist_set.set([dubois, bernard])
        self.stdout.write('Cliniques associées aux spécialistes')