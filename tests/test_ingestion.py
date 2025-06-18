import importlib
import os
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine


def test_upload_endpoint(monkeypatch, tmp_path):
    # Set required environment variables for Settings
    env_vars = {
        "POSTGRES_USER": "user",
        "POSTGRES_PASSWORD": "pass",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "db",
        "UPLOAD_DIR": str(tmp_path),
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    # Patch SQLAlchemy create_engine to use SQLite in tmp_path
    def fake_create_engine(*args, **kwargs):
        return create_engine(f"sqlite:///{tmp_path}/test.db", future=True)

    with mock.patch("sqlalchemy.create_engine", side_effect=fake_create_engine):
        import sys
        root_dir = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root_dir))
        ingest = importlib.reload(importlib.import_module("ingestion.ingest"))

    client = TestClient(ingest.app)

    test_file = tmp_path / "hello.txt"
    test_file.write_text("hello world")

    with test_file.open("rb") as f:
        response = client.post("/upload", files={"file": (test_file.name, f, "text/plain")})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    saved_file = Path(env_vars["UPLOAD_DIR"]) / data["filename"]
    assert saved_file.exists()
