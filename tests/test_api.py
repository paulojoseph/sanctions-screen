from fastapi.testclient import TestClient

from sanctions_screen import api
from tests.conftest import LISTS

client = TestClient(api.app)


def test_health(monkeypatch):
    monkeypatch.setenv("SANCTIONS_SCREEN_INDEX", str(LISTS))
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["entities"] > 1000


def test_screen_requires_name():
    assert client.post("/screen", json={}).status_code == 422
