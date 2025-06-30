from __future__ import annotations

from pathlib import Path
from typing import List
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseSettings
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    func,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
import weaviate
from sentence_transformers import SentenceTransformer

# Requires: pip install python-dotenv sqlalchemy weaviate-client sentence-transformers


class Settings(BaseSettings):
    WEAVIATE_URL: str
    WEAVIATE_API_KEY: str | None = None
    SENTENCE_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    TEXT_UPLOAD_DIR: str = "dhi.core/data/text_uploads/"

    class Config:
        env_file = Path(__file__).resolve().parents[1] / ".env"
        env_file_encoding = "utf-8"


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
settings = Settings()

text_dir = Path(settings.TEXT_UPLOAD_DIR)
text_dir.mkdir(parents=True, exist_ok=True)


Base = declarative_base()


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(String, primary_key=True)
    document_id = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def get_database_url(settings: Settings) -> str:
    return (
        f"postgresql://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


db_engine = create_engine(get_database_url(settings), future=True)
SessionLocal = sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)
Base.metadata.create_all(bind=db_engine)


auth = (
    weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY)
    if settings.WEAVIATE_API_KEY
    else None
)
client = weaviate.Client(url=settings.WEAVIATE_URL, auth_client_secret=auth)


existing = [c["class"] for c in client.schema.get().get("classes", [])]
if "Chunk" not in existing:
    chunk_schema = {
        "class": "Chunk",
        "vectorizer": "none",
        "properties": [
            {"name": "id", "dataType": ["string"], "description": "UUID of the chunk"},
            {"name": "document_id", "dataType": ["string"]},
            {"name": "chunk_index", "dataType": ["int"]},
            {"name": "text_content", "dataType": ["text"]},
        ],
    }
    client.schema.create_class(chunk_schema)


model = SentenceTransformer(settings.SENTENCE_MODEL_NAME)


def embed_text(text: str) -> List[float]:
    return model.encode(text).tolist()


def chunk_document(text: str, max_tokens: int = 500) -> List[str]:
    tokens = text.split()
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk = " ".join(tokens[i : i + max_tokens])
        chunks.append(chunk)
    return chunks


def process_all_documents() -> None:
    session = SessionLocal()
    for txt_file in text_dir.glob("*.txt"):
        document_id = txt_file.stem
        raw_text = txt_file.read_text(encoding="utf-8")
        chunks = chunk_document(raw_text)
        for i, chunk_text in enumerate(chunks):
            chunk_id = str(uuid4())
            embedding_vector = embed_text(chunk_text)
            client.data_object.create(
                data_object={
                    "id": chunk_id,
                    "document_id": document_id,
                    "chunk_index": i,
                    "text_content": chunk_text,
                },
                class_name="Chunk",
                vector=embedding_vector,
            )
            record = Chunk(
                id=chunk_id,
                document_id=document_id,
                chunk_index=i,
                text_content=chunk_text,
            )
            session.add(record)
            session.commit()
        print(f"Processed document {document_id} with {len(chunks)} chunks")
    session.close()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    process_all_documents()
