from fastapi import APIRouter, Depends, HTTPException
from backend.schemas import LoginRequest, Token, UserCreate
from backend.auth import verify_password, hash_password, create_token
from backend.deps import get_db, get_current_user
import psycopg2.extras

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
def login(body: LoginRequest, conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT u.*, r.nom as role_nom, r.permissions
        FROM utilisateurs u JOIN roles r ON u.role_id = r.id
        WHERE u.username = %s AND u.actif = TRUE
    """, (body.username,))
    user = cur.fetchone()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    cur.execute("UPDATE utilisateurs SET derniere_connexion = NOW() WHERE id = %s", (user["id"],))
    conn.commit()
    cur.close()

    token = create_token({"sub": str(user["id"])})
    return Token(
        access_token=token,
        user={
            "id": user["id"],
            "username": user["username"],
            "nom": user["nom"],
            "prenom": user["prenom"],
            "role": user["role_nom"],
            "permissions": user["permissions"],
        }
    )


@router.get("/me")
def me(user=Depends(get_current_user)):
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    return safe


@router.post("/init-admin")
def init_admin(body: UserCreate, conn=Depends(get_db)):
    """Bootstrap: creates first admin if none exist."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM utilisateurs")
    if cur.fetchone()[0] > 0:
        raise HTTPException(status_code=403, detail="Admin déjà initialisé")
    cur.execute("""
        INSERT INTO utilisateurs (username, email, password_hash, nom, prenom, role_id)
        VALUES (%s, %s, %s, %s, %s, (SELECT id FROM roles WHERE nom='admin'))
        RETURNING id
    """, (body.username, body.email, hash_password(body.password), body.nom, body.prenom))
    conn.commit()
    cur.close()
    return {"message": "Admin créé"}
