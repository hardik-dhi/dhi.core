"""FastAPI application for handling file uploads."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from .models import Base, Document


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    UPLOAD_DIR: str = os.path.join("dhi.core", "data", "uploads")

    class Config:
        env_file = Path(__file__).resolve().parents[1] / ".env"
        env_file_encoding = "utf-8"


def get_database_url(settings: Settings) -> str:
    """Construct the PostgreSQL database URL."""
    return (
        f"postgresql://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


settings = Settings()
load_dotenv(settings.Config.env_file)

UPLOAD_DIR_PATH = Path(settings.UPLOAD_DIR)
UPLOAD_DIR_PATH.mkdir(parents=True, exist_ok=True)

engine = create_engine(get_database_url(settings), future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    """Handle file upload and save metadata to the database."""
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    original_name = file.filename
    extension = os.path.splitext(original_name)[1]
    unique_name = f"{uuid4().hex}{extension}"
    destination = UPLOAD_DIR_PATH / unique_name

    try:
        contents = await file.read()
        destination.write_bytes(contents)
    except Exception as exc:  # pragma: no cover - runtime error handling
        raise HTTPException(status_code=400, detail=f"Failed to save file: {exc}")

    session = SessionLocal()
    document = Document(
        filename=unique_name,
        original_name=original_name,
        upload_time=datetime.utcnow(),
        media_type=file.content_type or "unknown",
    )
    session.add(document)
    session.commit()
    session.close()

    return JSONResponse(
        {
            "status": "success",
            "filename": unique_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
