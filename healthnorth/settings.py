"""
Django settings for healthnorth project.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Charge le fichier .env en local — sans effet sur Render (pas de .env,
# et les variables déjà définies dans l'environnement ne sont jamais écrasées)
load_dotenv(BASE_DIR / '.env')

# Clé secrète — obligatoire, lue uniquement depuis l'environnement
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "La variable d'environnement SECRET_KEY est absente. "
        "En local, copiez .env.example en .env et renseignez-la."
    )

# Debug désactivé par défaut — activé uniquement si DEBUG=True dans l'environnement
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1')

# Hôtes autorisés — Render + localhost pour le dev
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com']
CSRF_TRUSTED_ORIGINS = ['https://healthnorth.onrender.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'appointments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise : sert les fichiers statiques en production
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'healthnorth.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'healthnorth.wsgi.application'

# Base de données PostgreSQL — hébergée sur Neon en production (Render n'héberge
# que l'application), PostgreSQL local en développement
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ImproperlyConfigured(
        "La variable d'environnement DATABASE_URL est absente. "
        "En local, copiez .env.example en .env et renseignez-la."
    )
DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL)
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# Fichiers statiques
STATIC_URL = 'static/'
# Dossier où collectstatic rassemble tous les fichiers statiques pour la prod
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Fichiers media (uploads utilisateurs — ordonnances, certificats, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Stockage des documents médicaux sur Cloudflare R2 (compatible S3)
# Les 4 variables vont ensemble : toutes renseignées → R2, toutes vides → disque local
R2_SETTINGS = {
    name: os.environ.get(name, '')
    for name in ('R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_BUCKET_NAME', 'R2_ENDPOINT_URL')
}
R2_MISSING = [name for name, value in R2_SETTINGS.items() if not value]

if not R2_MISSING:
    DEFAULT_STORAGE = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'access_key': R2_SETTINGS['R2_ACCESS_KEY_ID'],
            'secret_key': R2_SETTINGS['R2_SECRET_ACCESS_KEY'],
            'bucket_name': R2_SETTINGS['R2_BUCKET_NAME'],
            # Endpoint juridiction EU : https://<ACCOUNT_ID>.eu.r2.cloudflarestorage.com
            'endpoint_url': R2_SETTINGS['R2_ENDPOINT_URL'],
            # R2 attend la région « auto » et la signature v4
            'region_name': 'auto',
            'signature_version': 's3v4',
            # Bucket privé : aucune ACL publique, pas de domaine public
            'default_acl': None,
            'custom_domain': None,
            # Accès uniquement via des URLs signées valables 5 minutes
            'querystring_auth': True,
            'querystring_expire': 300,
            # Jamais d'écrasement : un nom déjà pris reçoit un suffixe
            'file_overwrite': False,
            # Préfixe dans le bucket pour séparer local et production
            'location': os.environ.get('R2_LOCATION', ''),
        },
    }
elif len(R2_MISSING) < len(R2_SETTINGS):
    # Configuration partielle : on refuse de retomber silencieusement sur le disque
    # (sur Render, il est effacé à chaque redéploiement)
    raise ImproperlyConfigured(
        "Configuration R2 incomplète, variables manquantes : " + ', '.join(R2_MISSING)
    )
else:
    # Aucune variable R2 : stockage sur le disque local (développement)
    DEFAULT_STORAGE = {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    }

# Stockages (réglage STORAGES, Django 4.2+ — remplace STATICFILES_STORAGE supprimé en 5.1)
STORAGES = {
    # Fichiers uploadés : R2 ou disque local selon la configuration ci-dessus
    'default': DEFAULT_STORAGE,
    # WhiteNoise compresse et met en cache les fichiers statiques
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

AUTH_USER_MODEL = 'accounts.User'

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
LOGIN_URL = '/accounts/login/'