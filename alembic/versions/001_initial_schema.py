"""Schéma initial complet

Revision ID: 001
Revises:
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS vehicules (
            id           SERIAL PRIMARY KEY,
            plaque       TEXT NOT NULL,
            confidence   REAL,
            image_path   TEXT,
            timestamp    TIMESTAMP NOT NULL DEFAULT NOW(),
            point_entree TEXT DEFAULT 'Principal',
            notes        TEXT
        );

        CREATE TABLE IF NOT EXISTS conducteurs (
            id               SERIAL PRIMARY KEY,
            nom              TEXT,
            prenom           TEXT,
            numero_document  TEXT,
            type_document    TEXT,
            date_naissance   TEXT,
            nationalite      TEXT,
            date_expiration  TEXT,
            raw_scan         TEXT,
            timestamp        TIMESTAMP NOT NULL DEFAULT NOW(),
            point_entree     TEXT DEFAULT 'Principal',
            vehicule_id      INTEGER REFERENCES vehicules(id)
        );

        CREATE TABLE IF NOT EXISTS pietons (
            id               SERIAL PRIMARY KEY,
            nom              TEXT,
            prenom           TEXT,
            numero_document  TEXT,
            type_document    TEXT,
            date_naissance   TEXT,
            nationalite      TEXT,
            date_expiration  TEXT,
            raw_scan         TEXT,
            timestamp        TIMESTAMP NOT NULL DEFAULT NOW(),
            point_entree     TEXT DEFAULT 'Principal'
        );

        CREATE TABLE IF NOT EXISTS points_entree (
            id    SERIAL PRIMARY KEY,
            nom   TEXT UNIQUE NOT NULL,
            actif INTEGER DEFAULT 1
        );
        INSERT INTO points_entree (nom) VALUES ('Principal') ON CONFLICT (nom) DO NOTHING;
        INSERT INTO points_entree (nom) VALUES ('Entrée Nord') ON CONFLICT (nom) DO NOTHING;
        INSERT INTO points_entree (nom) VALUES ('Entrée Sud')  ON CONFLICT (nom) DO NOTHING;

        CREATE TABLE IF NOT EXISTS employes (
            id            SERIAL PRIMARY KEY,
            matricule     TEXT UNIQUE NOT NULL,
            nom           TEXT NOT NULL,
            prenom        TEXT NOT NULL,
            poste         TEXT,
            departement   TEXT,
            telephone     TEXT,
            email         TEXT,
            date_embauche TEXT,
            statut        TEXT DEFAULT 'Actif',
            timestamp     TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS roles (
            id          SERIAL PRIMARY KEY,
            nom         TEXT UNIQUE NOT NULL,
            permissions JSONB DEFAULT '{}'
        );
        INSERT INTO roles (nom, permissions) VALUES
          ('admin',       '{"all": true}'),
          ('superviseur', '{"read": true, "write": true, "reports": true, "blacklist": true}'),
          ('operateur',   '{"read": true, "write": true}'),
          ('lecteur',     '{"read": true}')
        ON CONFLICT (nom) DO NOTHING;

        CREATE TABLE IF NOT EXISTS utilisateurs (
            id                 SERIAL PRIMARY KEY,
            username           TEXT UNIQUE NOT NULL,
            email              TEXT UNIQUE,
            password_hash      TEXT NOT NULL,
            nom                TEXT,
            prenom             TEXT,
            role_id            INTEGER REFERENCES roles(id) DEFAULT 3,
            actif              BOOLEAN DEFAULT TRUE,
            derniere_connexion TIMESTAMP,
            timestamp          TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS cameras_ip (
            id                 SERIAL PRIMARY KEY,
            nom                TEXT NOT NULL,
            url_rtsp           TEXT NOT NULL,
            point_entree       TEXT DEFAULT 'Principal',
            actif              BOOLEAN DEFAULT TRUE,
            derniere_connexion TIMESTAMP,
            timestamp          TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS blacklist_plaques (
            id        SERIAL PRIMARY KEY,
            plaque    TEXT UNIQUE NOT NULL,
            motif     TEXT,
            severite  TEXT DEFAULT 'HAUTE',
            actif     BOOLEAN DEFAULT TRUE,
            cree_par  INTEGER REFERENCES utilisateurs(id),
            timestamp TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS blacklist_personnes (
            id               SERIAL PRIMARY KEY,
            numero_document  TEXT UNIQUE NOT NULL,
            nom              TEXT,
            prenom           TEXT,
            motif            TEXT,
            severite         TEXT DEFAULT 'HAUTE',
            actif            BOOLEAN DEFAULT TRUE,
            cree_par         INTEGER REFERENCES utilisateurs(id),
            timestamp        TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS alertes (
            id          SERIAL PRIMARY KEY,
            type        TEXT NOT NULL,
            message     TEXT,
            reference   TEXT,
            severite    TEXT DEFAULT 'HAUTE',
            traitee     BOOLEAN DEFAULT FALSE,
            traitee_par INTEGER REFERENCES utilisateurs(id),
            traitee_le  TIMESTAMP,
            camera_id   INTEGER REFERENCES cameras_ip(id),
            timestamp   TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS presences (
            id           SERIAL PRIMARY KEY,
            employe_id   INTEGER NOT NULL REFERENCES employes(id),
            type         TEXT NOT NULL CHECK (type IN ('ENTREE','SORTIE')),
            methode      TEXT DEFAULT 'BADGE',
            point_entree TEXT DEFAULT 'Principal',
            timestamp    TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_vehicules_plaque     ON vehicules(plaque);
        CREATE INDEX IF NOT EXISTS idx_vehicules_timestamp  ON vehicules(timestamp);
        CREATE INDEX IF NOT EXISTS idx_blacklist_plaques    ON blacklist_plaques(plaque);
        CREATE INDEX IF NOT EXISTS idx_blacklist_personnes  ON blacklist_personnes(numero_document);
        CREATE INDEX IF NOT EXISTS idx_alertes_traitee      ON alertes(traitee);
        CREATE INDEX IF NOT EXISTS idx_presences_employe    ON presences(employe_id);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS presences CASCADE;
        DROP TABLE IF EXISTS alertes CASCADE;
        DROP TABLE IF EXISTS blacklist_personnes CASCADE;
        DROP TABLE IF EXISTS blacklist_plaques CASCADE;
        DROP TABLE IF EXISTS cameras_ip CASCADE;
        DROP TABLE IF EXISTS utilisateurs CASCADE;
        DROP TABLE IF EXISTS roles CASCADE;
        DROP TABLE IF EXISTS employes CASCADE;
        DROP TABLE IF EXISTS points_entree CASCADE;
        DROP TABLE IF EXISTS pietons CASCADE;
        DROP TABLE IF EXISTS conducteurs CASCADE;
        DROP TABLE IF EXISTS vehicules CASCADE;
    """)
