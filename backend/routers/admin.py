from fastapi import APIRouter, Depends, HTTPException
from backend.deps import get_db, require_role
from backend.schemas import UserCreate, UserUpdate
from backend.auth import hash_password
import psycopg2.extras
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["Administration"])


def _s(rows):
    for r in rows:
        for k in ("timestamp", "derniere_connexion"):
            if isinstance(r.get(k), datetime):
                r[k] = r[k].isoformat()
        r.pop("password_hash", None)
    return rows


@router.get("/utilisateurs")
def list_users(conn=Depends(get_db), _=Depends(require_role("admin"))):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""SELECT u.*, r.nom as role_nom FROM utilisateurs u
                   JOIN roles r ON u.role_id=r.id ORDER BY u.timestamp DESC""")
    return _s([dict(r) for r in cur.fetchall()])


@router.post("/utilisateurs", status_code=201)
def create_user(body: UserCreate, conn=Depends(get_db), _=Depends(require_role("admin"))):
    cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO utilisateurs (username,email,password_hash,nom,prenom,role_id)
                       VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (body.username, body.email, hash_password(body.password),
                     body.nom, body.prenom, body.role_id))
        uid = cur.fetchone()[0]
        conn.commit()
        return {"id": uid}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(400, "Nom d'utilisateur ou email déjà utilisé")


@router.put("/utilisateurs/{uid}")
def update_user(uid: int, body: UserUpdate, conn=Depends(get_db), _=Depends(require_role("admin"))):
    cur = conn.cursor()
    if body.password:
        cur.execute("UPDATE utilisateurs SET password_hash=%s WHERE id=%s",
                    (hash_password(body.password), uid))
    updates = {k: v for k, v in body.dict(exclude={"password"}).items() if v is not None}
    if updates:
        sets = ", ".join(f"{k}=%s" for k in updates)
        cur.execute(f"UPDATE utilisateurs SET {sets} WHERE id=%s",
                    list(updates.values()) + [uid])
    conn.commit()
    return {"ok": True}


@router.delete("/utilisateurs/{uid}", status_code=204)
def delete_user(uid: int, conn=Depends(get_db), _=Depends(require_role("admin"))):
    cur = conn.cursor()
    cur.execute("DELETE FROM utilisateurs WHERE id=%s", (uid,))
    conn.commit()


@router.get("/roles")
def list_roles(conn=Depends(get_db), _=Depends(require_role("admin"))):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM roles ORDER BY id")
    return [dict(r) for r in cur.fetchall()]


@router.get("/logs")
def activity_logs(conn=Depends(get_db), _=Depends(require_role("admin"))):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT 'vehicule' as type, plaque as reference, timestamp FROM vehicules
        UNION ALL
        SELECT 'alerte', type || ': ' || COALESCE(reference,''), timestamp FROM alertes
        UNION ALL
        SELECT 'presence', e.matricule || ' ' || p.type, p.timestamp
        FROM presences p JOIN employes e ON p.employe_id=e.id
        ORDER BY timestamp DESC LIMIT 200
    """)
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if isinstance(r.get("timestamp"), datetime):
            r["timestamp"] = r["timestamp"].isoformat()
    return rows
