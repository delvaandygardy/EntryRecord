import pytest


@pytest.mark.asyncio
async def test_add_plaque_blacklist(client, auth_headers):
    payload = {"plaque": "BL-TEST-01", "motif": "Test", "severite": "HAUTE"}
    resp = await client.post("/api/blacklist/plaques", json=payload, headers=auth_headers)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_blacklist_plaques(client, auth_headers):
    resp = await client.get("/api/blacklist/plaques", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_duplicate_plaque_blacklist(client, auth_headers):
    payload = {"plaque": "BL-DUP-01", "motif": "Dup", "severite": "HAUTE"}
    r1 = await client.post("/api/blacklist/plaques", json=payload, headers=auth_headers)
    assert r1.status_code == 201
    r2 = await client.post("/api/blacklist/plaques", json=payload, headers=auth_headers)
    # L'API fait un upsert → toujours 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_add_personne_blacklist(client, auth_headers):
    payload = {
        "numero_document": "CNI-BL-9999",
        "nom": "Dupont",
        "prenom": "Jean",
        "motif": "Test",
        "severite": "MOYENNE",
    }
    resp = await client.post("/api/blacklist/personnes", json=payload, headers=auth_headers)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_blacklist_personnes(client, auth_headers):
    resp = await client.get("/api/blacklist/personnes", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
