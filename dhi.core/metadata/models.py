# Requires: pip install python-dotenv sqlalchemy psycopg2-binary

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.schema import ForeignKey


Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    media_type = Column(String, nullable=False)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    # Use JSON type for SQLite where ARRAY is unsupported
    tags = Column(ARRAY(String).with_variant(JSON, "sqlite"), default=list, nullable=False)
    processed_for_chunks = Column(Boolean, default=False)
    processed_for_graph = Column(Boolean, default=False)


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChartData(Base):
    __tablename__ = "chart_data"

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    axis_labels = Column(JSONB, nullable=False)
    series_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AudioTranscript(Base):
    __tablename__ = "audio_transcripts"

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    segment_index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def init_db():
    """Initialize the metadata database tables."""

    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)

    user = os.getenv("POSTGRES_USER", "")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "postgres")

    engine = create_engine(
        f"postgresql://{user}:{password}@{host}:{port}/{db}",
        future=True,
    )

    Base.metadata.create_all(engine)
    return engine


if __name__ == "__main__":
    init_db()
    print("Metadata tables created or already exist.")
