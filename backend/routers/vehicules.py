from fastapi import APIRouter, Depends, Query
from backend.deps import get_db, get_current_user, require_write
from backend.schemas import VehiculeCreate
import psycopg2.extras
from datetime import datetime

router = APIRouter(prefix="/api/vehicules", tags=["Véhicules"])


def _rows(cur): return [dict(r) for r in cur.fetchall()]
def _serialize(rows):
    for r in rows:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].isoformat()
    return rows


@router.get("")
def list_vehicules(limit: int = 200, q: str = Query(""), conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if q:
        cur.execute("SELECT * FROM vehicules WHERE plaque ILIKE %s ORDER BY timestamp DESC LIMIT %s",
                    (f"%{q}%", limit))
    else:
        cur.execute("SELECT * FROM vehicules ORDER BY timestamp DESC LIMIT %s", (limit,))
    return _serialize(_rows(cur))


@router.post("", status_code=201)
def create_vehicule(body: VehiculeCreate, conn=Depends(get_db), user=Depends(require_write)):
    cur = conn.cursor()
    # Check blacklist
    cur.execute("SELECT motif, severite FROM blacklist_plaques WHERE plaque = %s AND actif = TRUE",
                (body.plaque.upper().strip(),))
    bl = cur.fetchone()
    if bl:
        _create_alerte(conn, "BLACKLIST_PLAQUE", body.plaque.upper(), f"Plaque en liste noire: {bl[0]}", bl[1])

    cur.execute("""
        INSERT INTO vehicules (plaque, confidence, point_entree, notes)
        VALUES (%s, %s, %s, %s) RETURNING id
    """, (body.plaque.upper().strip(), body.confidence, body.point_entree, body.notes))
    vid = cur.fetchone()[0]
    conn.commit()
    return {"id": vid, "blacklist": bl is not None}


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
