"""
Fixtures pytest partagées.
Nécessite une base PostgreSQL de test :
  export TEST_DB_URL=postgresql://user:pass@localhost/enreg_test
  alembic upgrade head  (sur la base de test)
"""
import os
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pointer vers la BD de test avant d'importer l'app
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "enreg_test")
os.environ.setdefault("DB_USER", os.getenv("USER", "postgres"))
os.environ.setdefault("DB_PASSWORD", "")
os.environ.setdefault("SECRET_KEY", "test_secret_key_123")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def client():
    from backend.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="module")
async def auth_headers(client):
    """Crée un utilisateur admin de test et retourne ses headers JWT."""
    import psycopg2
    from backend.auth import hash_password
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"], port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO utilisateurs (username, password_hash, role_id)
        VALUES ('test_admin', %s, (SELECT id FROM roles WHERE nom='admin'))
        ON CONFLICT (username) DO NOTHING
    """, (hash_password("test_pass_123"),))
    conn.commit()
    conn.close()

    resp = await client.post("/api/auth/login",
                             json={"username": "test_admin", "password": "test_pass_123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
