-- =============================================================
-- HEALTH NORTH — Script de création de la base de données
-- Généré depuis les modèles Django (accounts + appointments)
-- SGBD : PostgreSQL
-- =============================================================

-- Suppression des tables dans l'ordre inverse des dépendances
DROP TABLE IF EXISTS appointments_document CASCADE;
DROP TABLE IF EXISTS appointments_appointment CASCADE;
DROP TABLE IF EXISTS appointments_specialist_clinics CASCADE;
DROP TABLE IF EXISTS appointments_specialist CASCADE;
DROP TABLE IF EXISTS appointments_clinic CASCADE;
DROP TABLE IF EXISTS appointments_examtype CASCADE;
DROP TABLE IF EXISTS appointments_specialty CASCADE;
DROP TABLE IF EXISTS accounts_user_groups CASCADE;
DROP TABLE IF EXISTS accounts_user_user_permissions CASCADE;
DROP TABLE IF EXISTS accounts_user CASCADE;

-- =============================================================
-- TABLE : accounts_user
-- Utilisateur étendu (hérite d'AbstractUser Django)
-- Joue le rôle de patient ET de spécialiste selon les cas
-- =============================================================
CREATE TABLE accounts_user (
    id                BIGSERIAL PRIMARY KEY,
    password          VARCHAR(128)    NOT NULL,
    last_login        TIMESTAMP WITH TIME ZONE,
    is_superuser      BOOLEAN         NOT NULL DEFAULT FALSE,
    username          VARCHAR(150)    NOT NULL UNIQUE,
    first_name        VARCHAR(150)    NOT NULL DEFAULT '',
    last_name         VARCHAR(150)    NOT NULL DEFAULT '',
    email             VARCHAR(254)    NOT NULL DEFAULT '',
    is_staff          BOOLEAN         NOT NULL DEFAULT FALSE,
    is_active         BOOLEAN         NOT NULL DEFAULT TRUE,
    date_joined       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    -- Champs ajoutés par le projet Health North
    phone             VARCHAR(20)     NOT NULL DEFAULT '',
    address           TEXT            NOT NULL DEFAULT '',
    date_of_birth     DATE
);

-- =============================================================
-- TABLE : accounts_user_groups (relation M2M Django auth)
-- =============================================================
CREATE TABLE accounts_user_groups (
    id       BIGSERIAL PRIMARY KEY,
    user_id  BIGINT NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL
);

-- =============================================================
-- TABLE : accounts_user_user_permissions (relation M2M Django auth)
-- =============================================================
CREATE TABLE accounts_user_user_permissions (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT  NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL
);

-- =============================================================
-- TABLE : appointments_specialty
-- Spécialité médicale (ex : Cardiologie, Radiologie)
-- =============================================================
CREATE TABLE appointments_specialty (
    id               BIGSERIAL PRIMARY KEY,
    name             VARCHAR(100) NOT NULL,
    duration_minutes INTEGER      NOT NULL DEFAULT 30
);

-- =============================================================
-- TABLE : appointments_examtype
-- Type d'examen médical (ex : Prise de sang, IRM, Scanner)
-- Rattaché à une spécialité via clé étrangère
-- =============================================================
CREATE TABLE appointments_examtype (
    id               BIGSERIAL    PRIMARY KEY,
    name             VARCHAR(200) NOT NULL,
    duration_minutes INTEGER      NOT NULL DEFAULT 30,
    description      TEXT         NOT NULL DEFAULT '',
    specialty_id     BIGINT       REFERENCES appointments_specialty(id) ON DELETE SET NULL
);

-- =============================================================
-- TABLE : appointments_clinic
-- Clinique ou laboratoire Health North sur le territoire français
-- Région stockée sous forme de slug (ex : 'ile-de-france')
-- =============================================================
CREATE TABLE appointments_clinic (
    id         BIGSERIAL    PRIMARY KEY,
    name       VARCHAR(200) NOT NULL,
    region     VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    city       VARCHAR(100) NOT NULL,
    address    VARCHAR(255) NOT NULL,
    phone      VARCHAR(20)  NOT NULL DEFAULT ''
);

-- Index pour optimiser les filtres par région et ville (utilisés dans les API JSON)
CREATE INDEX idx_clinic_region ON appointments_clinic(region);
CREATE INDEX idx_clinic_city   ON appointments_clinic(city);

-- =============================================================
-- TABLE : appointments_specialist
-- Médecin spécialiste lié à un compte utilisateur (OneToOne)
-- =============================================================
CREATE TABLE appointments_specialist (
    id           BIGSERIAL PRIMARY KEY,
    bio          TEXT      NOT NULL DEFAULT '',
    user_id      BIGINT    NOT NULL UNIQUE REFERENCES accounts_user(id) ON DELETE CASCADE,
    specialty_id BIGINT    REFERENCES appointments_specialty(id) ON DELETE SET NULL
);

-- =============================================================
-- TABLE : appointments_specialist_clinics
-- Table de liaison ManyToMany entre Specialist et Clinic
-- Un spécialiste peut exercer dans plusieurs cliniques
-- Une clinique peut accueillir plusieurs spécialistes
-- =============================================================
CREATE TABLE appointments_specialist_clinics (
    id            BIGSERIAL PRIMARY KEY,
    specialist_id BIGINT NOT NULL REFERENCES appointments_specialist(id) ON DELETE CASCADE,
    clinic_id     BIGINT NOT NULL REFERENCES appointments_clinic(id)     ON DELETE CASCADE,
    CONSTRAINT uq_specialist_clinic UNIQUE (specialist_id, clinic_id)
);

-- =============================================================
-- TABLE : appointments_appointment
-- Rendez-vous médical entre un patient et un spécialiste
-- Statuts possibles : pending / confirmed / cancelled
-- =============================================================
CREATE TABLE appointments_appointment (
    id            BIGSERIAL    PRIMARY KEY,
    date          TIMESTAMP WITH TIME ZONE NOT NULL,
    status        VARCHAR(20)  NOT NULL DEFAULT 'pending',
    notes         TEXT         NOT NULL DEFAULT '',
    patient_id    BIGINT       NOT NULL REFERENCES accounts_user(id)         ON DELETE CASCADE,
    specialist_id BIGINT       NOT NULL REFERENCES appointments_specialist(id) ON DELETE CASCADE,
    exam_type_id  BIGINT       REFERENCES appointments_examtype(id)           ON DELETE SET NULL,
    clinic_id     BIGINT       REFERENCES appointments_clinic(id)             ON DELETE SET NULL,
    -- Contrainte sur les valeurs du statut
    CONSTRAINT chk_status CHECK (status IN ('pending', 'confirmed', 'cancelled'))
);

-- Index pour optimiser la liste des RDV d'un patient (vue appointment_list)
CREATE INDEX idx_appointment_patient ON appointments_appointment(patient_id);

-- =============================================================
-- TABLE : appointments_document
-- Document médical déposé par le patient (ordonnance, certificat, etc.)
-- Stocké dans media/documents/ côté serveur
-- =============================================================
CREATE TABLE appointments_document (
    id             BIGSERIAL    PRIMARY KEY,
    file           VARCHAR(255) NOT NULL,
    document_type  VARCHAR(50)  NOT NULL DEFAULT 'autre',
    uploaded_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    appointment_id BIGINT       NOT NULL REFERENCES appointments_appointment(id) ON DELETE CASCADE,
    -- Contrainte sur les types de documents acceptés
    CONSTRAINT chk_document_type CHECK (
        document_type IN ('ordonnance', 'certificat', 'analyse', 'autre')
    )
);

-- =============================================================
-- DONNÉES DE TEST (valeurs minimales pour validation)
-- =============================================================

-- Spécialités
INSERT INTO appointments_specialty (name, duration_minutes) VALUES
    ('Cardiologie',   45),
    ('Radiologie',    60),
    ('Dermatologie',  30),
    ('Pédiatrie',     30),
    ('Ophtalmologie', 30);

-- Types d'examens
INSERT INTO appointments_examtype (name, duration_minutes, description, specialty_id) VALUES
    ('Électrocardiogramme (ECG)',    30, 'Enregistrement de l''activité électrique du cœur',     1),
    ('Échographie cardiaque',        60, 'Imagerie du cœur par ultrasons',                       1),
    ('IRM cérébrale',                60, 'Imagerie par résonance magnétique du cerveau',          2),
    ('Scanner thoracique',           45, 'Tomodensitométrie de la zone thoracique',               2),
    ('Dermoscopie',                  20, 'Examen de la peau par dermoscope',                      3),
    ('Biopsie cutanée',              30, 'Prélèvement d''un échantillon de peau',                 3),
    ('Consultation pédiatrique',     30, 'Consultation générale pour enfants',                    4),
    ('Bilan de croissance',          45, 'Suivi de la croissance de l''enfant',                   4),
    ('Fond d''œil',                  20, 'Examen de la rétine',                                   5),
    ('Champ visuel',                 30, 'Test du champ de vision',                               5),
    ('Prise de sang',                15, 'Prélèvement sanguin pour analyse',                      NULL),
    ('Radiographie',                 20, 'Imagerie par rayons X',                                 2),
    ('Échographie abdominale',       45, 'Imagerie de l''abdomen par ultrasons',                  2),
    ('Consultation générale',        30, 'Consultation médicale générale',                        NULL);

-- Cliniques
INSERT INTO appointments_clinic (name, region, department, city, address, phone) VALUES
    ('Clinique Saint-Louis',         'ile-de-france',          'Paris',           'Paris',    '12 rue de la Paix, 75001 Paris',             '01 42 00 00 01'),
    ('Centre Médical Lyon Sud',      'auvergne-rhone-alpes',   'Rhône',           'Lyon',     '5 avenue Jean Jaurès, 69007 Lyon',           '04 72 00 00 02'),
    ('Clinique Méditerranée',        'provence-alpes-cote-azur','Bouches-du-Rhône','Marseille','8 boulevard Michelet, 13008 Marseille',       '04 91 00 00 03'),
    ('Centre de Santé Bordeaux',     'nouvelle-aquitaine',     'Gironde',         'Bordeaux', '3 cours du Chapeau Rouge, 33000 Bordeaux',   '05 56 00 00 04'),
    ('Clinique du Nord',             'hauts-de-france',        'Nord',            'Lille',    '15 rue Nationale, 59000 Lille',              '03 20 00 00 05'),
    ('Centre Médical Toulouse',      'occitanie',              'Haute-Garonne',   'Toulouse', '22 allées Jean Jaurès, 31000 Toulouse',      '05 61 00 00 06');
