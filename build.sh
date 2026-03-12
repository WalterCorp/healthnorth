#!/usr/bin/env bash
# Script de build exécuté par Render à chaque déploiement

# Arrête le script si une commande échoue
set -o errexit

# Installe les dépendances Python
pip install -r requirements.txt

# Rassemble tous les fichiers statiques dans staticfiles/
python manage.py collectstatic --no-input

# Applique les migrations de base de données
python manage.py migrate

# Crée le superuser admin si il n'existe pas déjà
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@healthnorth.com', 'admin1234')
    print('Superuser créé')
else:
    print('Superuser existe déjà')
"