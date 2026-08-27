import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.config import settings, Settings

client = TestClient(app)

def test_settings_paths_and_defaults():
    """Verify settings resolve absolute paths and load correct defaults."""
    assert settings.app_name == "Role-Based RAG Interviewer"
    assert settings.app_version == "1.0.0"
    assert isinstance(settings.backend_dir, Path)
    assert settings.backend_dir.exists()
    assert "sqlite:///" in settings.database_url
    assert "chroma" in settings.chroma_path
    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) > 0

def test_cors_origins_validator():
    """Verify that CORS origins validator parses both lists and comma-separated strings."""
    custom_settings = Settings(cors_origins="http://example.com, https://app.example.com")
    assert custom_settings.cors_origins == ["http://example.com", "https://app.example.com"]

    json_settings = Settings(cors_origins='["http://test.com"]')
    assert json_settings.cors_origins == ["http://test.com"]

def test_root_endpoint():
    """Verify GET / returns application information and docs link."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == settings.app_name
    assert data["version"] == settings.app_version
    assert data["status"] == "running"
    assert data["docs"] == "/docs"

def test_health_endpoint():
    """Verify GET /health returns 200 OK and database connectivity."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["app"] == settings.app_name
    assert data["version"] == settings.app_version

def test_cors_headers():
    """Verify that CORS middleware headers are sent for allowed origin."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    vercel_response = client.options(
        "/health",
        headers={
            "Origin": "https://frontend-eight-green-24.vercel.app",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert vercel_response.headers.get("access-control-allow-origin") == "https://frontend-eight-green-24.vercel.app"

def test_validation_error_handler():
    """Verify that validation errors return structured 422 JSON."""
    response = client.post("/interview/sessions", json={})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["status_code"] == 422
    assert data["error_type"] == "ValidationError"
