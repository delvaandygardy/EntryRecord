import psycopg2
import psycopg2.extras
from datetime import datetime
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DUPLICATE_WINDOW


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS vehicules (
            id          SERIAL PRIMARY KEY,
            plaque      TEXT NOT NULL,
            confidence  REAL,
            image_path  TEXT,
            timestamp   TIMESTAMP NOT NULL DEFAULT NOW(),
            point_entree TEXT DEFAULT 'Principal',
            notes       TEXT
        )
    """)

    c.execute("""
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
        )
    """)

    c.execute("""
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
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS points_entree (
            id   SERIAL PRIMARY KEY,
            nom  TEXT UNIQUE NOT NULL,
            actif INTEGER DEFAULT 1
        )
    """)

    c.execute("INSERT INTO points_entree (nom) VALUES ('Principal')  ON CONFLICT (nom) DO NOTHING")
    c.execute("INSERT INTO points_entree (nom) VALUES ('Entrée Nord') ON CONFLICT (nom) DO NOTHING")
    c.execute("INSERT INTO points_entree (nom) VALUES ('Entrée Sud')  ON CONFLICT (nom) DO NOTHING")

    c.execute("""
        CREATE TABLE IF NOT EXISTS employes (
            id               SERIAL PRIMARY KEY,
            matricule        TEXT UNIQUE NOT NULL,
            nom              TEXT NOT NULL,
            prenom           TEXT NOT NULL,
            poste            TEXT,
            departement      TEXT,
            telephone        TEXT,
            email            TEXT,
            date_embauche    TEXT,
            statut           TEXT DEFAULT 'Actif',
            timestamp        TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    conn.commit()
    c.close()
    conn.close()


def insert_vehicule(plaque, confidence=None, image_path=None, point_entree="Principal", notes=None):
    if is_duplicate_vehicule(plaque):
        return None
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO vehicules (plaque, confidence, image_path, timestamp, point_entree, notes)
        VALUES (%s, %s, %s, NOW(), %s, %s)
        RETURNING id
        """,
        (plaque.upper().strip(), confidence, image_path, point_entree, notes)
    )
    row_id = c.fetchone()[0]
    conn.commit()
    c.close()
    conn.close()
    return row_id


def insert_conducteur(data: dict, vehicule_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO conducteurs
            (nom, prenom, numero_document, type_document, date_naissance, nationalite,
             date_expiration, raw_scan, timestamp, point_entree, vehicule_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        RETURNING id
        """,
        (
            data.get("nom"), data.get("prenom"), data.get("numero_document"),
            data.get("type_document", "PERMIS"), data.get("date_naissance"),
            data.get("nationalite"), data.get("date_expiration"),
            data.get("raw_scan"),
            data.get("point_entree", "Principal"), vehicule_id
        )
    )
    row_id = c.fetchone()[0]
    conn.commit()
    c.close()
    conn.close()
    return row_id


def insert_pieton(data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO pietons
            (nom, prenom, numero_document, type_document, date_naissance, nationalite,
             date_expiration, raw_scan, timestamp, point_entree)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        RETURNING id
        """,
        (
            data.get("nom"), data.get("prenom"), data.get("numero_document"),
            data.get("type_document", "CNI"), data.get("date_naissance"),
            data.get("nationalite"), data.get("date_expiration"),
            data.get("raw_scan"),
            data.get("point_entree", "Principal")
        )
    )
    row_id = c.fetchone()[0]
    conn.commit()
    c.close()
    conn.close()
    return row_id


def insert_employe(data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO employes
            (matricule, nom, prenom, poste, departement, telephone, email,
             date_embauche, statut)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            data.get("matricule", "").upper().strip(),
            data.get("nom", "").strip(),
            data.get("prenom", "").strip(),
            data.get("poste"),
            data.get("departement"),
            data.get("telephone"),
            data.get("email"),
            data.get("date_embauche"),
            data.get("statut", "Actif"),
        )
    )
    row_id = c.fetchone()[0]
    conn.commit()
    c.close()
    conn.close()
    return row_id


def update_employe(record_id: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        UPDATE employes SET
            matricule    = %s,
            nom          = %s,
            prenom       = %s,
            poste        = %s,
            departement  = %s,
            telephone    = %s,
            email        = %s,
            date_embauche = %s,
            statut       = %s
        WHERE id = %s
        """,
        (
            data.get("matricule", "").upper().strip(),
            data.get("nom", "").strip(),
            data.get("prenom", "").strip(),
            data.get("poste"),
            data.get("departement"),
            data.get("telephone"),
            data.get("email"),
            data.get("date_embauche"),
            data.get("statut", "Actif"),
            record_id,
        )
    )
    conn.commit()
    c.close()
    conn.close()


def fetch_employes(statut=None, limit=500):
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if statut:
        c.execute(
            "SELECT * FROM employes WHERE statut = %s ORDER BY nom, prenom LIMIT %s",
            (statut, limit)
        )
    else:
        c.execute("SELECT * FROM employes ORDER BY nom, prenom LIMIT %s", (limit,))
    rows = _serialize_rows(c.fetchall())
    c.close()
    conn.close()
    return rows


def search_employes(query: str):
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    like = f"%{query}%"
    c.execute(
        """
        SELECT * FROM employes
        WHERE nom ILIKE %s OR prenom ILIKE %s OR matricule ILIKE %s
           OR poste ILIKE %s OR departement ILIKE %s
        ORDER BY nom, prenom
        """,
        (like, like, like, like, like)
    )
    rows = _serialize_rows(c.fetchall())
    c.close()
    conn.close()
    return rows


def is_duplicate_vehicule(plaque):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM vehicules WHERE plaque = %s AND timestamp > NOW() - INTERVAL '%s seconds'",
        (plaque.upper().strip(), DUPLICATE_WINDOW)
    )
    result = c.fetchone()
    c.close()
    conn.close()
    return result is not None


def fetch_recent(table, limit=200):
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute(
        f"SELECT * FROM {table} ORDER BY timestamp DESC LIMIT %s",
        (limit,)
    )
    rows = [dict(r) for r in c.fetchall()]
    # Serialize timestamps to string for UI compatibility
    for row in rows:
        if isinstance(row.get("timestamp"), datetime):
            row["timestamp"] = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    c.close()
    conn.close()
    return rows


def fetch_stats():
    conn = get_connection()
    c = conn.cursor()
    stats = {}
    for table in ("vehicules", "conducteurs", "pietons"):
        c.execute(f"SELECT COUNT(*) FROM {table}")
        stats[f"{table}_total"] = c.fetchone()[0]
        c.execute(
            f"SELECT COUNT(*) FROM {table} WHERE timestamp::date = CURRENT_DATE"
        )
        stats[f"{table}_today"] = c.fetchone()[0]
    c.close()
    conn.close()
    return stats


def search_records(query, tables=None):
    if tables is None:
        tables = ["vehicules", "conducteurs", "pietons"]
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    results = {}
    like = f"%{query}%"

    if "vehicules" in tables:
        c.execute(
            "SELECT * FROM vehicules WHERE plaque ILIKE %s ORDER BY timestamp DESC",
            (like,)
        )
        results["vehicules"] = _serialize_rows(c.fetchall())

    for table in ("conducteurs", "pietons"):
        if table in tables:
            c.execute(
                f"""
                SELECT * FROM {table}
                WHERE nom ILIKE %s OR prenom ILIKE %s OR numero_document ILIKE %s
                ORDER BY timestamp DESC
                """,
                (like, like, like)
            )
            results[table] = _serialize_rows(c.fetchall())

    c.close()
    conn.close()
    return results


def get_points_entree():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT nom FROM points_entree WHERE actif = 1 ORDER BY nom")
    rows = [r[0] for r in c.fetchall()]
    c.close()
    conn.close()
    return rows


def delete_record(table, record_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(f"DELETE FROM {table} WHERE id = %s", (record_id,))
    conn.commit()
    c.close()
    conn.close()


def _serialize_rows(rows):
    result = []
    for row in rows:
        d = dict(row)
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        result.append(d)
    return result
