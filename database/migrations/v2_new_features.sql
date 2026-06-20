-- v2: Nouvelles tables pour les fonctionnalités avancées

-- Rôles utilisateurs
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

-- Utilisateurs
CREATE TABLE IF NOT EXISTS utilisateurs (
    id            SERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    nom           TEXT,
    prenom        TEXT,
    role_id       INTEGER REFERENCES roles(id) DEFAULT 3,
    actif         BOOLEAN DEFAULT TRUE,
    derniere_connexion TIMESTAMP,
    timestamp     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Caméras IP
CREATE TABLE IF NOT EXISTS cameras_ip (
    id                  SERIAL PRIMARY KEY,
    nom                 TEXT NOT NULL,
    url_rtsp            TEXT NOT NULL,
    point_entree        TEXT DEFAULT 'Principal',
    actif               BOOLEAN DEFAULT TRUE,
    derniere_connexion  TIMESTAMP,
    timestamp           TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Liste noire plaques
CREATE TABLE IF NOT EXISTS blacklist_plaques (
    id        SERIAL PRIMARY KEY,
    plaque    TEXT UNIQUE NOT NULL,
    motif     TEXT,
    severite  TEXT DEFAULT 'HAUTE',
    actif     BOOLEAN DEFAULT TRUE,
    cree_par  INTEGER REFERENCES utilisateurs(id),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Liste noire personnes
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

-- Alertes
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

-- Présences employés (badgeage)
CREATE TABLE IF NOT EXISTS presences (
    id          SERIAL PRIMARY KEY,
    employe_id  INTEGER NOT NULL REFERENCES employes(id),
    type        TEXT NOT NULL CHECK (type IN ('ENTREE','SORTIE')),
    methode     TEXT DEFAULT 'BADGE',
    point_entree TEXT DEFAULT 'Principal',
    timestamp   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index pour performances
CREATE INDEX IF NOT EXISTS idx_blacklist_plaques_plaque ON blacklist_plaques(plaque);
CREATE INDEX IF NOT EXISTS idx_blacklist_personnes_doc  ON blacklist_personnes(numero_document);
CREATE INDEX IF NOT EXISTS idx_alertes_traitee          ON alertes(traitee);
CREATE INDEX IF NOT EXISTS idx_presences_employe        ON presences(employe_id);
CREATE INDEX IF NOT EXISTS idx_vehicules_timestamp      ON vehicules(timestamp);
