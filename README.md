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

> Les mots de passe des comptes de test sont disponibles sur demande auprès du développeur.

## 🛠️ Stack technique

- **Backend** : Django 6 / Python 3.12
- **Base de données** : PostgreSQL (Supabase)
- **Hébergement** : Render.com
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

## 📦 Installation locale
```bash
git clone https://github.com/WalterCorp/healthnorth.git
cd healthnorth
python -m venv env
source env/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata appointments/fixtures/initial_data.json
python manage.py seed
python manage.py runserver
```

## 📁 Documentation

Tous les livrables sont disponibles dans le dossier [`docs/`](docs/) :

| Document | Description |
|----------|-------------|
| `healthnorth_documentation.docx` | MCD, diagramme de classes, script SQL |
| `healthnorth_maquettes_IHM.docx` | Maquettes application web |
| `healthnorth_maquettes_mobile_lourde.docx` | Maquettes mobile et application lourde |
| `healthnorth_protocole_tests_api.docx` | Protocole de tests API Bruno |
| `healthnorth_infrastructure_M4_M5.docx` | Infrastructure, tickets, authentification |
| `healthnorth_schema.sql` | Script SQL PostgreSQL |

## 🎓 Contexte

Projet réalisé dans le cadre du **BTS SIO option B SLAM** — Épreuve E6.
