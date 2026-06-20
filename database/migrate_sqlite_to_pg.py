"""
Migration SQLite → PostgreSQL
Usage: python database/migrate_sqlite_to_pg.py
"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import get_connection, init_db

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "registrations.db")


def migrate():
    if not os.path.exists(SQLITE_PATH):
        print("Aucune base SQLite trouvée. Rien à migrer.")
        return

    print("Initialisation de la base PostgreSQL…")
    init_db()

    sq = sqlite3.connect(SQLITE_PATH)
    sq.row_factory = sqlite3.Row
    sc = sq.cursor()

    pg = get_connection()
    pc = pg.cursor()

    tables = {
        "vehicules": (
            "(plaque, confidence, image_path, timestamp, point_entree, notes)",
            "(%s, %s, %s, %s, %s, %s)",
            lambda r: (r["plaque"], r["confidence"], r["image_path"],
                       r["timestamp"], r["point_entree"], r["notes"])
        ),
        "conducteurs": (
            "(nom, prenom, numero_document, type_document, date_naissance, nationalite, "
            "date_expiration, raw_scan, timestamp, point_entree, vehicule_id)",
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            lambda r: (r["nom"], r["prenom"], r["numero_document"], r["type_document"],
                       r["date_naissance"], r["nationalite"], r["date_expiration"],
                       r["raw_scan"], r["timestamp"], r["point_entree"], r["vehicule_id"])
        ),
        "pietons": (
            "(nom, prenom, numero_document, type_document, date_naissance, nationalite, "
            "date_expiration, raw_scan, timestamp, point_entree)",
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            lambda r: (r["nom"], r["prenom"], r["numero_document"], r["type_document"],
                       r["date_naissance"], r["nationalite"], r["date_expiration"],
                       r["raw_scan"], r["timestamp"], r["point_entree"])
        ),
    }

    for table, (cols, placeholders, extractor) in tables.items():
        sc.execute(f"SELECT * FROM {table} ORDER BY id")
        rows = sc.fetchall()
        if not rows:
            print(f"  {table}: 0 enregistrements.")
            continue
        count = 0
        for row in rows:
            try:
                pc.execute(
                    f"INSERT INTO {table} {cols} VALUES {placeholders}",
                    extractor(row)
                )
                count += 1
            except Exception as e:
                print(f"  Erreur ligne {dict(row)}: {e}")
        pg.commit()
        print(f"  {table}: {count} enregistrements migrés.")

    pc.close()
    pg.close()
    sq.close()
    print("\nMigration terminée.")


if __name__ == "__main__":
    migrate()
