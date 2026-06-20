import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_list_vehicules(client, auth_headers):
    resp = await client.get("/api/vehicules", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_vehicule(client, auth_headers):
    payload = {"plaque": "HA-TEST-99", "confidence": 0.95, "point_entree": "Principal"}
    resp = await client.post("/api/vehicules", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_create_vehicule_blacklisted(client, auth_headers):
    """Une plaque en liste noire doit créer une alerte au passage."""
    # Ajouter la plaque en liste noire
    bl = await client.post("/api/blacklist/plaques",
                           json={"plaque": "BL-BAD-00", "motif": "Volé", "severite": "HAUTE"},
                           headers=auth_headers)
    assert bl.status_code == 201

    # Enregistrer la plaque
    resp = await client.post("/api/vehicules",
                             json={"plaque": "BL-BAD-00", "point_entree": "Principal"},
                             headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json().get("blacklist") is True


@pytest.mark.asyncio
async def test_delete_vehicule(client, auth_headers):
    # Créer un véhicule, puis le supprimer
    create = await client.post("/api/vehicules",
                               json={"plaque": "TO-DEL-01", "point_entree": "Principal"},
                               headers=auth_headers)
    vid = create.json()["id"]
    resp = await client.delete(f"/api/vehicules/{vid}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_search_vehicule(client, auth_headers):
    await client.post("/api/vehicules",
                      json={"plaque": "SR-CH-77", "point_entree": "Principal"},
                      headers=auth_headers)
    resp = await client.get("/api/vehicules?q=SR-CH", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert any("SR-CH" in v["plaque"] for v in results)
