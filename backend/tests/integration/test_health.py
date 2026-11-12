from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import Settings


def test_health_returns_ok() -> None:
    client = TestClient(create_app(Settings(jwt_secret="test", rate_limit_enabled=False)))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
