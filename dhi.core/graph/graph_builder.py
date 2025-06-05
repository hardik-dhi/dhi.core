from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Text, Integer, Boolean, func
from sqlalchemy.orm import sessionmaker, declarative_base
from neo4j import GraphDatabase
import spacy

# Requires: pip install python-dotenv sqlalchemy neo4j spacy
# Also: python -m spacy download en_core_web_sm


class Settings:
    """Application settings loaded from .env or environment."""

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    NEO4J_URL: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    def __init__(self) -> None:
        env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(env_path)
        self.POSTGRES_USER = os.getenv("POSTGRES_USER", "")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
        self.POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
        self.NEO4J_URL = os.getenv("NEO4J_URL", "bolt://localhost:7687")
        self.NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
        self.NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "test")


settings = Settings()


Base = declarative_base()


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(String, primary_key=True)
    document_id = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    graph_processed = Column(Boolean, default=False)


def get_database_url(settings: Settings) -> str:
    return (
        f"postgresql://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


engine = create_engine(get_database_url(settings), future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


# Neo4j driver setup
neo4j_driver = GraphDatabase.driver(settings.NEO4J_URL, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))


def get_neo4j_session():
    return neo4j_driver.session()


# spaCy setup
nlp = spacy.load("en_core_web_sm")


def extract_entities(text: str) -> List[Tuple[str, str]]:
    """Run spaCy NER on text and return deduplicated (entity_text, entity_label)."""
    doc = nlp(text)
    seen = set()
    entities: List[Tuple[str, str]] = []
    for ent in doc.ents:
        if ent.text not in seen:
            seen.add(ent.text)
            entities.append((ent.text, ent.label_))
    return entities


def merge_document(tx, document_id: str):
    tx.run("""
        MERGE (d:Document {id: $document_id})
    """, document_id=document_id)


def merge_chunk(tx, chunk_id: str, chunk_index: int, text: str, document_id: str):
    tx.run(
        """
        MERGE (c:Chunk {id: $chunk_id})
        SET c.chunk_index = $chunk_index, c.text = $text_content
        MERGE (d:Document {id: $document_id})
        MERGE (c)-[:BELONGS_TO_DOCUMENT]->(d)
        """,
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        text_content=text,
        document_id=document_id,
    )


def merge_entity(tx, entity_text: str, entity_label: str):
    tx.run(
        """
        MERGE (e:Entity {name: $entity_text, label: $entity_label})
        """,
        entity_text=entity_text,
        entity_label=entity_label,
    )


def merge_mentions(tx, chunk_id: str, entity_text: str, entity_label: str):
    tx.run(
        """
        MERGE (c:Chunk {id: $chunk_id})
        MERGE (e:Entity {name: $entity_text, label: $entity_label})
        MERGE (c)-[:MENTIONS]->(e)
        """,
        chunk_id=chunk_id,
        entity_text=entity_text,
        entity_label=entity_label,
    )


def build_graph() -> None:
    session = SessionLocal()
    try:
        chunks = session.query(Chunk).filter(Chunk.graph_processed == False).all()
        for chunk in chunks:
            entities = extract_entities(chunk.text_content)
            with get_neo4j_session() as neo_session:
                neo_session.write_transaction(merge_document, chunk.document_id)
                neo_session.write_transaction(
                    merge_chunk,
                    chunk.id,
                    chunk.chunk_index,
                    chunk.text_content,
                    chunk.document_id,
                )
                for entity_text, entity_label in entities:
                    neo_session.write_transaction(merge_entity, entity_text, entity_label)
                    neo_session.write_transaction(
                        merge_mentions, chunk.id, entity_text, entity_label
                    )
            chunk.graph_processed = True
            session.add(chunk)
            session.commit()
            logging.info(
                "Processed chunk %s with %s entities", chunk.id, len(entities)
            )
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_graph()
