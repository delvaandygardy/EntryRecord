from fastapi import APIRouter, Depends, Query, Body, HTTPException
from backend.deps import get_db, get_current_user, require_write
from backend.schemas import PersonneCreate
import psycopg2.extras
from datetime import datetime

router = APIRouter(tags=["Personnes"])

def _s(rows):
    for r in rows:
        for field in ("timestamp", "heure_sortie"):
            if isinstance(r.get(field), datetime):
                r[field] = r[field].isoformat()
    return rows

def _check_blacklist(conn, numero_document):
    cur = conn.cursor()
    cur.execute("SELECT motif, severite FROM blacklist_personnes WHERE numero_document=%s AND actif=TRUE",
                (numero_document,))
    return cur.fetchone()


@router.get("/api/conducteurs")
def list_conducteurs(limit: int = 200, q: str = Query(""), conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if q:
        cur.execute("""SELECT * FROM conducteurs WHERE nom ILIKE %s OR prenom ILIKE %s
                       OR numero_document ILIKE %s ORDER BY timestamp DESC LIMIT %s""",
                    (f"%{q}%",)*3 + (limit,))
    else:
        cur.execute("SELECT * FROM conducteurs ORDER BY timestamp DESC LIMIT %s", (limit,))
    return _s([dict(r) for r in cur.fetchall()])


@router.post("/api/conducteurs", status_code=201)
def create_conducteur(body: PersonneCreate, conn=Depends(get_db), _=Depends(require_write)):
    bl = _check_blacklist(conn, body.numero_document or "")
    if bl:
        cur = conn.cursor()
        cur.execute("""INSERT INTO alertes (type, message, reference, severite)
                       VALUES ('BLACKLIST_PERSONNE',%s,%s,%s)""",
                    (f"Conducteur en liste noire: {bl[0]}", body.numero_document, bl[1]))
        conn.commit()
    cur = conn.cursor()
    cur.execute("""INSERT INTO conducteurs (nom,prenom,numero_document,type_document,
                   date_naissance,nationalite,date_expiration,point_entree)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (body.nom, body.prenom, body.numero_document, body.type_document,
                 body.date_naissance, body.nationalite, body.date_expiration, body.point_entree))
    cid = cur.fetchone()[0]
    conn.commit()
    return {"id": cid, "blacklist": bl is not None}


@router.patch("/api/conducteurs/{cid}/sortie", status_code=200)
def sortie_conducteur(cid: int, body: dict = Body(default={}), conn=Depends(get_db), _=Depends(require_write)):
    point = (body or {}).get("point_sortie", "Principal")
    cur = conn.cursor()
    cur.execute("UPDATE conducteurs SET heure_sortie=NOW(), point_sortie=%s WHERE id=%s AND heure_sortie IS NULL",
                (point, cid))
    if cur.rowcount == 0:
        raise HTTPException(400, "Sortie déjà enregistrée ou conducteur introuvable")
    conn.commit()
    return {"message": "Sortie enregistrée"}


@router.delete("/api/conducteurs/{cid}", status_code=204)
def delete_conducteur(cid: int, conn=Depends(get_db), _=Depends(require_write)):
    cur = conn.cursor()
    cur.execute("DELETE FROM conducteurs WHERE id=%s", (cid,))
    conn.commit()


@router.get("/api/pietons")
def list_pietons(limit: int = 200, q: str = Query(""), conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if q:
        cur.execute("""SELECT * FROM pietons WHERE nom ILIKE %s OR prenom ILIKE %s
                       OR numero_document ILIKE %s ORDER BY timestamp DESC LIMIT %s""",
                    (f"%{q}%",)*3 + (limit,))
    else:
        cur.execute("SELECT * FROM pietons ORDER BY timestamp DESC LIMIT %s", (limit,))
    return _s([dict(r) for r in cur.fetchall()])


@router.post("/api/pietons", status_code=201)
def create_pieton(body: PersonneCreate, conn=Depends(get_db), _=Depends(require_write)):
    bl = _check_blacklist(conn, body.numero_document or "")
    if bl:
        cur = conn.cursor()
        cur.execute("""INSERT INTO alertes (type, message, reference, severite)
                       VALUES ('BLACKLIST_PERSONNE',%s,%s,%s)""",
                    (f"Piéton en liste noire: {bl[0]}", body.numero_document, bl[1]))
        conn.commit()
    cur = conn.cursor()
    cur.execute("""INSERT INTO pietons (nom,prenom,numero_document,type_document,
                   date_naissance,nationalite,date_expiration,point_entree)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (body.nom, body.prenom, body.numero_document, body.type_document,
                 body.date_naissance, body.nationalite, body.date_expiration, body.point_entree))
    pid = cur.fetchone()[0]
    conn.commit()
    return {"id": pid, "blacklist": bl is not None}


@router.patch("/api/pietons/{pid}/sortie", status_code=200)
def sortie_pieton(pid: int, body: dict = Body(default={}), conn=Depends(get_db), _=Depends(require_write)):
    point = (body or {}).get("point_sortie", "Principal")
    cur = conn.cursor()
    cur.execute("UPDATE pietons SET heure_sortie=NOW(), point_sortie=%s WHERE id=%s AND heure_sortie IS NULL",
                (point, pid))
    if cur.rowcount == 0:
        raise HTTPException(400, "Sortie déjà enregistrée ou piéton introuvable")
    conn.commit()
    return {"message": "Sortie enregistrée"}


@router.delete("/api/pietons/{pid}", status_code=204)
def delete_pieton(pid: int, conn=Depends(get_db), _=Depends(require_write)):
    cur = conn.cursor()
    cur.execute("DELETE FROM pietons WHERE id=%s", (pid,))
    conn.commit()
