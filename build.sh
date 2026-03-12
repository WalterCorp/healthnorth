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

# Charge les données initiales (spécialités, examens, cliniques)
python manage.py loaddata appointments/fixtures/initial_data.json

# Crée les utilisateurs de test et associe les cliniques
python scripts/seed.py