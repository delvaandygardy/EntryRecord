import pytest


@pytest.mark.asyncio
async def test_login_success(client, auth_headers):
    resp = await client.post("/api/auth/login",
                             json={"username": "test_admin", "password": "test_pass_123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post("/api/auth/login",
                             json={"username": "test_admin", "password": "mauvais"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_no_token(client):
    resp = await client.get("/api/vehicules")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_invalid_token(client):
    resp = await client.get("/api/vehicules",
                            headers={"Authorization": "Bearer token_invalide"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
