"""Tests de l'application accounts — affichage des erreurs de connexion."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

# Début du message d'erreur de Django en français (identifiants incorrects)
INVALID_LOGIN_MESSAGE = 'et un mot de passe valides'


class LoginErrorDisplayTests(TestCase):
    """La page de connexion affiche les erreurs générales du formulaire."""

    @classmethod
    def setUpTestData(cls):
        """Crée un utilisateur de test."""
        cls.user = User.objects.create_user('login_user', password='pw-test-login-1')
        cls.url = reverse('login')

    def test_wrong_password_shows_error_alert(self):
        """Mauvais mot de passe : le formulaire est réaffiché avec une alerte rouge."""
        response = self.client.post(self.url, {'username': 'login_user', 'password': 'faux'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="alert alert-danger')
        self.assertContains(response, INVALID_LOGIN_MESSAGE)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_unknown_username_shows_same_error(self):
        """Identifiant inexistant : même message, sans révéler si le compte existe."""
        response = self.client.post(self.url, {'username': 'inexistant', 'password': 'faux'})
        self.assertContains(response, INVALID_LOGIN_MESSAGE)

    def test_no_error_on_first_display(self):
        """Premier affichage de la page : aucune alerte d'erreur."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="alert alert-danger')

    def test_valid_login_still_redirects(self):
        """Identifiants corrects : connexion et redirection vers l'accueil."""
        response = self.client.post(self.url, {'username': 'login_user', 'password': 'pw-test-login-1'})
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
