import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from backend.auth import decode_token
import psycopg2
import psycopg2.extras
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db():
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                             user=DB_USER, password=DB_PASSWORD)
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(token: str = Depends(oauth2_scheme), conn=Depends(get_db)):
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        user_id: int = int(sub) if sub is not None else None
        if user_id is None:
            raise cred_exc
    except JWTError:
        raise cred_exc

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT u.*, r.nom as role_nom, r.permissions
        FROM utilisateurs u
        JOIN roles r ON u.role_id = r.id
        WHERE u.id = %s AND u.actif = TRUE
    """, (user_id,))
    user = cur.fetchone()
    cur.close()
    if not user:
        raise cred_exc
    return dict(user)


def require_role(*roles):
    def checker(user=Depends(get_current_user)):
        perms = user.get("permissions", {})
        if perms.get("all") or user.get("role_nom") in roles:
            return user
        raise HTTPException(status_code=403, detail="Permission insuffisante")
    return checker


def require_write(user=Depends(get_current_user)):
    perms = user.get("permissions", {})
    if not (perms.get("all") or perms.get("write")):
        raise HTTPException(status_code=403, detail="Accès en écriture requis")
    return user
