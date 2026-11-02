# Health North 🏥

Application web de réservation de rendez-vous médicaux en ligne.

## 🚀 Démo en production

**URL** : https://healthnorth.onrender.com

### Comptes de test

| Rôle | Username |
|------|----------|
| Patient | `patient1` |
| Administrateur | `admin` |
| Dr. Martin (Cardio) | `dr.martin` |
| Dr. Dubois (Radio) | `dr.dubois` |
| Dr. Bernard (Dermato) | `dr.bernard` |
| Dr. Leroy (Pédiatre) | `dr.leroy` |

> Les mots de passe des comptes de test sont disponibles sur demande auprès du développeur.

## 🛠️ Stack technique

- **Backend** : Django 6 / Python 3.12
- **Base de données** : PostgreSQL serverless (Neon)
- **Hébergement** : Render.com (application uniquement)
- **Stockage des documents** : Cloudflare R2 (compatible S3, bucket privé, juridiction EU)
- **Frontend** : Bootstrap 5.3 + Bootstrap Icons
- **Tests API** : Bruno (collection dans `bruno/`)

## 📋 Fonctionnalités

- Inscription et connexion patient
- Modification du profil et du mot de passe
- Prise de rendez-vous en cascade (région → ville → clinique → spécialiste → examen → date)
- Modification et annulation de rendez-vous
- Dépôt de documents médicaux (ordonnances, certificats)
- Backoffice administrateur Django
- API JSON + CRUD complet

## 🗂️ Structure du projet
```
healthnorth/
├── accounts/          # Application gestion utilisateurs
├── appointments/      # Application rendez-vous et API
├── templates/         # Templates HTML Django
├── bruno/             # Collection de tests API Bruno
├── docs/              # Documentation et livrables du projet
└── healthnorth/       # Configuration Django
```

## 💻 Lancer le projet en local

### Prérequis

- Python 3.12
- PostgreSQL installé et démarré en local

### 1. Cloner le dépôt et installer les dépendances
```bash
git clone https://github.com/WalterCorp/healthnorth.git
cd healthnorth
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### 2. Créer la base de données locale
```bash
createdb healthnorth
```

### 3. Configurer les variables d'environnement

Les secrets ne sont jamais écrits dans le code : ils sont lus depuis un fichier `.env`
(non versionné), chargé automatiquement au démarrage grâce à `python-dotenv`.
```bash
cp .env.example .env
```

Renseignez ensuite les valeurs dans `.env` :

| Variable | Rôle |
|----------|------|
| `SECRET_KEY` | Clé secrète Django (obligatoire) |
| `DEBUG` | `True` en local uniquement — désactivé par défaut |
| `DATABASE_URL` | URL de connexion à votre PostgreSQL local, au format `postgresql://UTILISATEUR:MOT_DE_PASSE@localhost:5432/healthnorth` |
| `SEED_ADMIN_PASSWORD` | Mot de passe du compte de test `admin` |
| `SEED_PATIENT_PASSWORD` | Mot de passe du compte de test `patient1` |
| `SEED_DOCTOR_PASSWORD` | Mot de passe commun aux 4 comptes médecins |
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | Clé API R2 (facultatif en local, voir ci-dessous) |
| `R2_BUCKET_NAME` | Nom du bucket R2 |
| `R2_ENDPOINT_URL` | Endpoint R2 de la juridiction EU : `https://<ACCOUNT_ID>.eu.r2.cloudflarestorage.com` |
| `R2_LOCATION` | Préfixe des fichiers dans le bucket (ex. `local`) — facultatif |

Pour générer une `SECRET_KEY` :
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> Si `SECRET_KEY` ou `DATABASE_URL` est absente, Django s'arrête avec une erreur `ImproperlyConfigured` explicite.

> Les variables `SEED_*` ne servent qu'à la commande `python manage.py seed`, qui crée les
> comptes de test. Si l'une d'elles est vide, le compte concerné n'est pas créé et un
> avertissement s'affiche (sans erreur). Un compte déjà existant n'est jamais modifié :
> son mot de passe n'est pas réinitialisé.

### 4. Initialiser la base et lancer le serveur
```bash
python manage.py migrate
python manage.py loaddata appointments/fixtures/initial_data.json
python manage.py seed
python manage.py runserver
```

L'application est disponible sur http://127.0.0.1:8000.

> En production (Render), ces variables sont définies dans le tableau de bord Render
> et `DATABASE_URL` pointe vers la base Neon.

## 🧪 Tests API avec Bruno

La collection [Bruno](https://www.usebruno.com/) se trouve dans `bruno/Health North API/`,
avec deux environnements : `Local` (http://127.0.0.1:8000) et `Production`.

**Mot de passe de connexion.** La requête « POST login » lit le mot de passe du compte
`patient1` dans la variable `PATIENT_PASSWORD`, définie dans un fichier `.env` **local et
non versionné**, à la racine de la collection (méthode recommandée par Bruno) :

```bash
cd "bruno/Health North API"
cp .env.example .env
```

Renseignez ensuite `PATIENT_PASSWORD` dans ce `.env` : le mot de passe de `patient1` sur la
base locale (valeur de `SEED_PATIENT_PASSWORD`) pour l'environnement `Local`, ou son mot de
passe de production pour l'environnement `Production`. Rouvrez ensuite la collection dans
Bruno pour qu'il relise le fichier.

> Le fichier `.env` de la collection est ignoré par Git (`.gitignore` de la collection) ;
> seul `.env.example`, sans valeur, est versionné.

**Authentification.** Les requêtes protégées nécessitent une session : exécutez d'abord
« GET login page (CSRF) », reportez le jeton CSRF et le cookie dans les variables
`csrfToken` et `csrfCookie` de l'environnement, puis exécutez « POST login ».

## 🔒 Stockage et accès aux documents médicaux

Les documents déposés par les patients (ordonnances, certificats, résultats d'analyse)
sont des données de santé : ils ne sont jamais accessibles par une URL publique.

**Stockage.** En production, les fichiers sont stockés sur **Cloudflare R2** (via
`django-storages`, compatible S3) et non sur le disque de Render, qui est effacé à chaque
redéploiement. Le bucket est **privé** (aucune ACL publique, aucun domaine public) et
situé dans la **juridiction EU** : les données restent dans l'Union européenne.
Un fichier existant n'est jamais écrasé. Quand un document est supprimé (admin, suppression
du rendez-vous ou code), son fichier est aussi supprimé du stockage, une fois la suppression
en base validée.

**Validation.** Chaque dépôt est contrôlé côté serveur (l'attribut HTML `accept` ne suffit
pas) : formats **PDF, JPG, JPEG, PNG** uniquement, **5 Mo maximum**, **contenu conforme à
l'extension** (les premiers octets du fichier sont comparés à la signature PDF, PNG ou JPEG :
un texte ou un exécutable renommé en `.pdf` est refusé) et type de document limité aux
choix proposés. Les erreurs s'affichent en français dans le formulaire.

**Contrôle d'accès.** Les liens vers les documents passent par la vue
`appointments/documents/<id>/download/`, qui :

1. exige d'être connecté ;
2. vérifie que l'utilisateur est le **patient** du rendez-vous, le **spécialiste** du
   rendez-vous ou un **superutilisateur** — sinon elle renvoie une erreur 404, sans
   révéler l'existence du document ;
3. redirige vers une **URL signée valable 5 minutes**, générée à la demande.
   Passé ce délai, le lien est refusé par R2.

**En local.** R2 est facultatif :

- **sans R2** (les 4 variables `R2_*` vides) : les fichiers sont stockés dans `media/`
  (non versionné) et servis par la même vue sécurisée — il n'existe pas de route `/media/` ;
- **avec R2** : renseignez les 4 variables et `R2_LOCATION=local`, pour que vos fichiers
  de test soient rangés sous le préfixe `local/` et jamais mélangés à ceux de production.

> Une configuration R2 incomplète (certaines variables seulement) arrête Django avec une
> erreur `ImproperlyConfigured`, pour ne jamais retomber silencieusement sur le disque.

## 📁 Documentation

Tous les livrables sont disponibles dans le dossier [`docs/`](docs/) :

| Document | Description |
|----------|-------------|
| `healthnorth_documentation.pdf` | MCD, diagramme de classes, script SQL |
| `healthnorth_maquettes_IHM.pdf` | Maquettes application web |
| `healthnorth_maquettes_mobile_lourde.pdf` | Maquettes mobile et application lourde |
| `healthnorth_protocole_tests_api.pdf` | Protocole de tests API Bruno |
| `healthnorth_infrastructure_M4_M5.pdf` | Infrastructure, tickets, authentification |
| `healthnorth_schema.sql` | Script SQL PostgreSQL |

## 🎓 Contexte

Projet réalisé dans le cadre du **BTS SIO option B SLAM** — Épreuve E6.
