"""Commande Django pour peupler la base de données en production."""

# pylint: disable=no-member
import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from appointments.models import Specialist, Specialty, Clinic

User = get_user_model()

# Comptes de test — les mots de passe sont lus depuis l'environnement,
# jamais écrits dans le code (dépôt public)
TEST_ACCOUNTS = [
    {
        'username': 'admin', 'email': 'admin@healthnorth.com',
        'password_env': 'SEED_ADMIN_PASSWORD', 'is_superuser': True,
    },
    {
        'username': 'patient1', 'email': 'patient1@healthnorth.com',
        'first_name': 'Jean', 'last_name': 'Dupont',
        'password_env': 'SEED_PATIENT_PASSWORD',
    },
    # Médecins — specialty_id correspond aux spécialités chargées par la fixture
    {
        'username': 'dr.martin', 'email': 'martin@healthnorth.com',
        'first_name': 'Pierre', 'last_name': 'Martin',
        'password_env': 'SEED_DOCTOR_PASSWORD', 'specialty_id': 1,
    },
    {
        'username': 'dr.dubois', 'email': 'dubois@healthnorth.com',
        'first_name': 'Sophie', 'last_name': 'Dubois',
        'password_env': 'SEED_DOCTOR_PASSWORD', 'specialty_id': 2,
    },
    {
        'username': 'dr.bernard', 'email': 'bernard@healthnorth.com',
        'first_name': 'Claire', 'last_name': 'Bernard',
        'password_env': 'SEED_DOCTOR_PASSWORD', 'specialty_id': 3,
    },
    {
        'username': 'dr.leroy', 'email': 'leroy@healthnorth.com',
        'first_name': 'Marc', 'last_name': 'Leroy',
        'password_env': 'SEED_DOCTOR_PASSWORD', 'specialty_id': 4,
    },
]

# Association cliniques — spécialistes (pk de la clinique → médecins)
CLINIC_SPECIALISTS = {
    1: ['dr.martin', 'dr.dubois'],
    2: ['dr.martin', 'dr.bernard'],
    3: ['dr.dubois', 'dr.leroy'],
    4: ['dr.bernard', 'dr.leroy'],
    5: ['dr.martin', 'dr.leroy'],
    6: ['dr.dubois', 'dr.bernard'],
}


class Command(BaseCommand):
    """Crée les utilisateurs de test et associe les cliniques aux spécialistes."""

    help = "Peuple la base de données avec les données de test"

    def handle(self, *args, **options):
        """Exécute le script de peuplement."""
        for account in TEST_ACCOUNTS:
            self.create_account(account)
        self.link_clinics()

    @transaction.atomic
    def create_account(self, account):
        """Crée un compte de test s'il n'existe pas — un compte existant n'est jamais modifié.

        Transaction atomique : si la création du profil spécialiste échoue,
        le compte utilisateur est annulé lui aussi (jamais de compte créé à moitié).
        """
        username = account['username']
        user = User.objects.filter(username=username).first()

        if user is None:
            password = os.environ.get(account['password_env'])
            if not password:
                # Pas d'erreur : le build Render ne doit jamais échouer pour un compte de test
                self.stdout.write(self.style.WARNING(
                    f"Compte '{username}' non créé : "
                    f"variable {account['password_env']} absente"
                ))
                return
            if account.get('is_superuser'):
                user = User.objects.create_superuser(username, account['email'], password)
            else:
                user = User.objects.create_user(username, account['email'], password)
                user.first_name = account['first_name']
                user.last_name = account['last_name']
                user.save()
            created = True
        else:
            created = False

        # Médecin : crée le profil spécialiste s'il manque (sans toucher au compte)
        specialist_created = False
        if 'specialty_id' in account and not Specialist.objects.filter(user=user).exists():
            Specialist.objects.create(
                user=user, specialty=Specialty.objects.get(pk=account['specialty_id'])
            )
            specialist_created = True

        # Messages affichés seulement une fois la création complète réussie
        if created:
            self.stdout.write(f'{username} créé')
        if specialist_created:
            self.stdout.write(f'Specialist {username} créé')

    def link_clinics(self):
        """Associe les cliniques aux spécialistes, si tous les médecins existent."""
        usernames = {name for names in CLINIC_SPECIALISTS.values() for name in names}
        specialists = {
            s.user.username: s
            for s in Specialist.objects.filter(user__username__in=usernames).select_related('user')
        }
        missing = sorted(usernames - specialists.keys())
        if missing:
            self.stdout.write(self.style.WARNING(
                'Association cliniques ignorée : spécialistes manquants '
                f"({', '.join(missing)})"
            ))
            return

        for clinic_id, names in CLINIC_SPECIALISTS.items():
            Clinic.objects.get(pk=clinic_id).specialist_set.set(
                [specialists[name] for name in names]
            )
        self.stdout.write('Cliniques associées aux spécialistes')
