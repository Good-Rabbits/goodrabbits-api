import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # Use TestClient with lifespan context manager disabled for isolated unit testing
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    # Test that the public health check endpoint responds with 200 and healthy status
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
