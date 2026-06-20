from fastapi import APIRouter, Depends
from backend.deps import get_db, get_current_user, require_role
from backend.schemas import BlacklistPlaqueCreate, BlacklistPersonneCreate
import psycopg2.extras
from datetime import datetime

router = APIRouter(prefix="/api/blacklist", tags=["Liste noire"])

def _s(rows):
    for r in rows:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].isoformat()
    return rows


@router.get("/plaques")
def list_blacklist_plaques(conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM blacklist_plaques ORDER BY timestamp DESC")
    return _s([dict(r) for r in cur.fetchall()])


@router.post("/plaques", status_code=201)
def add_blacklist_plaque(body: BlacklistPlaqueCreate, conn=Depends(get_db),
                          user=Depends(require_role("admin", "superviseur"))):
    cur = conn.cursor()
    cur.execute("""INSERT INTO blacklist_plaques (plaque, motif, severite, cree_par)
                   VALUES (%s,%s,%s,%s) ON CONFLICT (plaque) DO UPDATE
                   SET motif=%s, severite=%s, actif=TRUE RETURNING id""",
                (body.plaque.upper(), body.motif, body.severite, user["id"],
                 body.motif, body.severite))
    bid = cur.fetchone()[0]
    conn.commit()
    return {"id": bid}


@router.delete("/plaques/{bid}", status_code=204)
def remove_blacklist_plaque(bid: int, conn=Depends(get_db),
                             _=Depends(require_role("admin", "superviseur"))):
    cur = conn.cursor()
    cur.execute("UPDATE blacklist_plaques SET actif=FALSE WHERE id=%s", (bid,))
    conn.commit()


@router.get("/personnes")
def list_blacklist_personnes(conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM blacklist_personnes ORDER BY timestamp DESC")
    return _s([dict(r) for r in cur.fetchall()])


@router.post("/personnes", status_code=201)
def add_blacklist_personne(body: BlacklistPersonneCreate, conn=Depends(get_db),
                            user=Depends(require_role("admin", "superviseur"))):
    cur = conn.cursor()
    cur.execute("""INSERT INTO blacklist_personnes (numero_document,nom,prenom,motif,severite,cree_par)
                   VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (numero_document) DO UPDATE
                   SET nom=%s,prenom=%s,motif=%s,severite=%s,actif=TRUE RETURNING id""",
                (body.numero_document, body.nom, body.prenom, body.motif, body.severite, user["id"],
                 body.nom, body.prenom, body.motif, body.severite))
    bid = cur.fetchone()[0]
    conn.commit()
    return {"id": bid}


@router.delete("/personnes/{bid}", status_code=204)
def remove_blacklist_personne(bid: int, conn=Depends(get_db),
                               _=Depends(require_role("admin", "superviseur"))):
    cur = conn.cursor()
    cur.execute("UPDATE blacklist_personnes SET actif=FALSE WHERE id=%s", (bid,))
    conn.commit()


@router.get("/check/plaque/{plaque}")
def check_plaque(plaque: str, conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM blacklist_plaques WHERE plaque=%s AND actif=TRUE",
                (plaque.upper(),))
    r = cur.fetchone()
    return {"blacklisted": r is not None, "details": dict(r) if r else None}


@router.get("/check/personne/{numero_document}")
def check_personne(numero_document: str, conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM blacklist_personnes WHERE numero_document=%s AND actif=TRUE",
                (numero_document,))
    r = cur.fetchone()
    return {"blacklisted": r is not None, "details": dict(r) if r else None}
