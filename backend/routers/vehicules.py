from fastapi import APIRouter, Depends, Query, HTTPException, Body
from backend.deps import get_db, get_current_user, require_write
from backend.schemas import VehiculeCreate
import psycopg2.extras
from datetime import datetime

router = APIRouter(prefix="/api/vehicules", tags=["Véhicules"])


def _rows(cur): return [dict(r) for r in cur.fetchall()]
def _serialize(rows):
    for r in rows:
        for f in ("timestamp", "heure_sortie"):
            if isinstance(r.get(f), datetime):
                r[f] = r[f].isoformat()
    return rows


@router.get("")
def list_vehicules(limit: int = 200, q: str = Query(""), conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    base = """
        SELECT v.*, c.nom AS conducteur_nom, c.prenom AS conducteur_prenom
        FROM vehicules v
        LEFT JOIN conducteurs c ON v.conducteur_id = c.id
    """
    if q:
        cur.execute(base + " WHERE v.plaque ILIKE %s ORDER BY v.timestamp DESC LIMIT %s",
                    (f"%{q}%", limit))
    else:
        cur.execute(base + " ORDER BY v.timestamp DESC LIMIT %s", (limit,))
    return _serialize(_rows(cur))


@router.post("", status_code=201)
def create_vehicule(body: VehiculeCreate, conn=Depends(get_db), user=Depends(require_write)):
    cur = conn.cursor()
    plaque = body.plaque.upper().strip()

    cur.execute("SELECT motif, severite FROM blacklist_plaques WHERE plaque = %s AND actif = TRUE", (plaque,))
    bl = cur.fetchone()
    if bl:
        _create_alerte(conn, "BLACKLIST_PLAQUE", plaque, f"Plaque en liste noire: {bl[0]}", bl[1])

    # Sortie automatique : si une entrée ouverte existe pour cette plaque → enregistrer la sortie
    cur.execute("""
        SELECT id FROM vehicules
        WHERE plaque = %s AND heure_sortie IS NULL
        ORDER BY timestamp DESC LIMIT 1
    """, (plaque,))
    open_entry = cur.fetchone()

    if open_entry:
        vid = open_entry[0]
        cur.execute("""
            UPDATE vehicules
            SET heure_sortie = NOW(), point_sortie = %s
            WHERE id = %s
        """, (body.point_entree, vid))
        conn.commit()
        return {"id": vid, "action": "SORTIE", "blacklist": bl is not None, "conducteur_lie": False}

    # Nouvelle entrée
    conducteur_id = body.conducteur_id
    if not conducteur_id:
        cur.execute("""
            SELECT c.id FROM conducteurs c
            WHERE c.point_entree = %s
              AND c.heure_sortie IS NULL
              AND c.timestamp > NOW() - INTERVAL '15 minutes'
              AND NOT EXISTS (
                  SELECT 1 FROM vehicules v
                  WHERE v.conducteur_id = c.id AND v.heure_sortie IS NULL
              )
            ORDER BY c.timestamp DESC LIMIT 1
        """, (body.point_entree,))
        row = cur.fetchone()
        if row:
            conducteur_id = row[0]

    cur.execute("""
        INSERT INTO vehicules (plaque, confidence, point_entree, notes, conducteur_id, type_vehicule, region_plaque, couleur_vehicule)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    """, (plaque, body.confidence, body.point_entree, body.notes, conducteur_id,
          body.type_vehicule, body.region_plaque, body.couleur_vehicule))
    vid = cur.fetchone()[0]
    conn.commit()
    return {"id": vid, "action": "ENTREE", "blacklist": bl is not None, "conducteur_lie": conducteur_id is not None}


@router.patch("/{vid}/sortie")
def sortie_vehicule(vid: int, point_sortie: str = Body("Principal", embed=True),
                    conn=Depends(get_db), _=Depends(require_write)):
    cur = conn.cursor()
    cur.execute(
        "UPDATE vehicules SET heure_sortie=NOW(), point_sortie=%s WHERE id=%s AND heure_sortie IS NULL RETURNING id",
        (point_sortie, vid),
    )
    if cur.fetchone() is None:
        raise HTTPException(404, "Véhicule introuvable ou déjà sorti")
    conn.commit()
    return {"ok": True}


@router.delete("/{vid}", status_code=204)
def delete_vehicule(vid: int, conn=Depends(get_db), _=Depends(require_write)):
    cur = conn.cursor()
    cur.execute("DELETE FROM vehicules WHERE id = %s", (vid,))
    conn.commit()


def _create_alerte(conn, type_, reference, message, severite="HAUTE", camera_id=None):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO alertes (type, message, reference, severite, camera_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (type_, message, reference, severite, camera_id))
    conn.commit()
