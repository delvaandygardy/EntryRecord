from fastapi import APIRouter, Depends, HTTPException
from backend.deps import get_db, get_current_user, require_write
from pydantic import BaseModel
import psycopg2.extras

router = APIRouter(prefix="/api/points_acces", tags=["Points d'accès"])


class PointCreate(BaseModel):
    nom: str


class PointUpdate(BaseModel):
    nom: str


@router.get("")
def list_points(conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, nom, actif FROM points_acces WHERE actif = TRUE ORDER BY id")
    return [dict(r) for r in cur.fetchall()]


@router.post("", status_code=201)
def create_point(body: PointCreate, conn=Depends(get_db), _=Depends(require_write)):
    nom = body.nom.strip()
    if not nom:
        raise HTTPException(400, "Nom requis")
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO points_acces (nom) VALUES (%s) RETURNING id", (nom,)
        )
        pid = cur.fetchone()[0]
        conn.commit()
        return {"id": pid, "nom": nom}
    except Exception:
        conn.rollback()
        raise HTTPException(409, "Ce point d'accès existe déjà")


@router.patch("/{pid}")
def update_point(pid: int, body: PointUpdate, conn=Depends(get_db), _=Depends(require_write)):
    nom = body.nom.strip()
    if not nom:
        raise HTTPException(400, "Nom requis")
    cur = conn.cursor()
    cur.execute(
        "UPDATE points_acces SET nom = %s WHERE id = %s AND actif = TRUE RETURNING id",
        (nom, pid),
    )
    if cur.fetchone() is None:
        raise HTTPException(404, "Point d'accès introuvable")
    conn.commit()
    return {"ok": True}


@router.delete("/{pid}", status_code=204)
def delete_point(pid: int, conn=Depends(get_db), _=Depends(require_write)):
    cur = conn.cursor()
    cur.execute("SELECT nom FROM points_acces WHERE id = %s AND actif = TRUE", (pid,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "Point d'accès introuvable")
    if row[0] == "Principal":
        raise HTTPException(400, "Le point 'Principal' ne peut pas être supprimé")
    cur.execute("UPDATE points_acces SET actif = FALSE WHERE id = %s", (pid,))
    conn.commit()
