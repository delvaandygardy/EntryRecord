from fastapi import APIRouter, Depends, Query, HTTPException
from backend.deps import get_db, get_current_user, require_write
from backend.schemas import EmployeCreate, BadgeRequest, PresenceCreate
import psycopg2.extras
from datetime import datetime

router = APIRouter(prefix="/api/employes", tags=["Employés"])

def _s(rows):
    for r in rows:
        for k in ("timestamp",):
            if isinstance(r.get(k), datetime):
                r[k] = r[k].isoformat()
    return rows


@router.get("")
def list_employes(statut: str = Query(""), q: str = Query(""), conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    sql = "SELECT * FROM employes"
    params = []
    where = []
    if statut and statut != "Tous":
        where.append("statut = %s"); params.append(statut)
    if q:
        where.append("(nom ILIKE %s OR prenom ILIKE %s OR matricule ILIKE %s OR poste ILIKE %s)")
        params += [f"%{q}%"]*4
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY nom, prenom"
    cur.execute(sql, params)
    return _s([dict(r) for r in cur.fetchall()])


@router.post("", status_code=201)
def create_employe(body: EmployeCreate, conn=Depends(get_db), _=Depends(require_write)):
    cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO employes (matricule,nom,prenom,poste,departement,telephone,email,date_embauche,statut)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (body.matricule.upper(), body.nom, body.prenom, body.poste, body.departement,
                     body.telephone, body.email, body.date_embauche, body.statut))
        eid = cur.fetchone()[0]
        conn.commit()
        return {"id": eid}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(400, "Matricule déjà existant")


@router.put("/{eid}")
def update_employe(eid: int, body: EmployeCreate, conn=Depends(get_db), _=Depends(require_write)):
    cur = conn.cursor()
    cur.execute("""UPDATE employes SET matricule=%s,nom=%s,prenom=%s,poste=%s,departement=%s,
                   telephone=%s,email=%s,date_embauche=%s,statut=%s WHERE id=%s""",
                (body.matricule.upper(), body.nom, body.prenom, body.poste, body.departement,
                 body.telephone, body.email, body.date_embauche, body.statut, eid))
    conn.commit()
    return {"ok": True}


@router.delete("/{eid}", status_code=204)
def delete_employe(eid: int, conn=Depends(get_db), _=Depends(require_write)):
    cur = conn.cursor()
    cur.execute("DELETE FROM employes WHERE id=%s", (eid,))
    conn.commit()


# ── Badgeage ──────────────────────────────────────────────────────────────

@router.post("/badge")
def badge(body: BadgeRequest, conn=Depends(get_db), _=Depends(get_current_user)):
    """Badgeage employé : détecte auto ENTREE ou SORTIE selon dernier badge."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, nom, prenom, statut FROM employes WHERE matricule=%s",
                (body.matricule.upper(),))
    emp = cur.fetchone()
    if not emp:
        raise HTTPException(404, "Matricule introuvable")
    if emp["statut"] != "Actif":
        raise HTTPException(403, "Employé inactif")

    cur.execute("""SELECT type FROM presences WHERE employe_id=%s
                   ORDER BY timestamp DESC LIMIT 1""", (emp["id"],))
    last = cur.fetchone()
    ptype = "SORTIE" if (last and last["type"] == "ENTREE") else "ENTREE"

    cur2 = conn.cursor()
    cur2.execute("""INSERT INTO presences (employe_id, type, methode, point_entree)
                    VALUES (%s,%s,'BADGE',%s) RETURNING id""",
                 (emp["id"], ptype, body.point_entree))
    pid = cur2.fetchone()[0]
    conn.commit()
    return {"id": pid, "type": ptype, "employe": dict(emp)}


@router.get("/{eid}/presences")
def get_presences(eid: int, limit: int = 100, conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""SELECT p.*, e.nom, e.prenom, e.matricule FROM presences p
                   JOIN employes e ON p.employe_id=e.id
                   WHERE p.employe_id=%s ORDER BY p.timestamp DESC LIMIT %s""", (eid, limit))
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].isoformat()
    return rows


@router.get("/presences/today")
def presences_today(conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""SELECT p.*, e.nom, e.prenom, e.matricule, e.poste
                   FROM presences p JOIN employes e ON p.employe_id=e.id
                   WHERE p.timestamp::date = CURRENT_DATE
                   ORDER BY p.timestamp DESC""")
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].isoformat()
    return rows
