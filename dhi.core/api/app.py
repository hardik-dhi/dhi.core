# Requires: pip install fastapi uvicorn python-dotenv sqlalchemy psycopg2-binary weaviate-client neo4j sentence-transformers spacy Pillow chartocr
# Also: python -m spacy download en_core_web_sm

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables from .env located one level up
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# Postgres (for metadata)
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")

# Weaviate (vector DB)
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

# Neo4j (graph DB)
NEO4J_URL = os.getenv("NEO4J_URL")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Other upload directories
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "dhi.core/data/uploads/")
UPLOAD_DIR_AUDIO = os.getenv("UPLOAD_DIR_AUDIO", "dhi.core/data/audio_uploads/")
UPLOAD_DIR_IMAGE = os.getenv("UPLOAD_DIR_IMAGE", "dhi.core/data/image_uploads/")
UPLOAD_DIR_CHART = os.getenv("UPLOAD_DIR_CHART", "dhi.core/data/chart_uploads/")
TEXT_UPLOAD_DIR = os.getenv("TEXT_UPLOAD_DIR", "dhi.core/data/text_uploads/")

# FastAPI application
app = FastAPI(
    title="DHI Core API",
    description="Unified API for ingesting, searching, and graph-querying multimodal knowledge",
    version="0.1.0",
)

# SQLAlchemy setup
from metadata.models import Base  # ensures metadata is defined
from metadata.models import Document, Chunk, ChartData, AudioTranscript

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Weaviate client setup
import weaviate

if WEAVIATE_API_KEY:
    weaviate_auth = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
    weaviate_client = weaviate.Client(url=WEAVIATE_URL, auth_client_secret=weaviate_auth)
else:
    weaviate_client = weaviate.Client(url=WEAVIATE_URL)

# Neo4j driver setup
from neo4j import GraphDatabase

neo4j_driver = GraphDatabase.driver(
    NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD)
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_neo4j_write(cypher: str, parameters: Dict[str, Any] | None = None) -> None:
    with neo4j_driver.session() as session:
        session.write_transaction(lambda tx: tx.run(cypher, parameters or {}))


def run_neo4j_read(cypher: str, parameters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    with neo4j_driver.session() as session:
        result = session.read_transaction(lambda tx: tx.run(cypher, parameters or {}))
        return [record.data() for record in result]


def process_upload_task(document_id: str, path: str) -> None:
    """Background task to embed chunks and build graph for a document."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - runtime issue
        # Cannot process file without text
        return

    process_document(document_id, text)
    build_graph()

    session = SessionLocal()
    try:
        doc = session.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processed_for_graph = True
            session.add(doc)
            session.commit()
    finally:
        session.close()


@app.post("/upload", summary="Upload a new file to be ingested")
async def upload_file(
    file: UploadFile = File(...),
    media_type: str = Form(...),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    - Save the uploaded file in UPLOAD_DIR/<uuid>.<ext>
    - Insert a Document row in PostgreSQL with:
        id=uuid, filename=saved_name, original_name=file.filename, media_type, upload_time=now
    """
    import uuid

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1]
    doc_id = str(uuid.uuid4())
    saved_filename = f"{doc_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)

    try:
        with open(file_path, "wb") as buffer:
            contents = await file.read()
            buffer.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    new_doc = Document(
        id=doc_id,
        filename=saved_filename,
        original_name=file.filename,
        media_type=media_type,
    )
    try:
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    background_tasks.add_task(process_upload_task, doc_id, file_path)

    return {"status": "success", "document_id": doc_id, "saved_name": saved_filename}


from transcription.transcribe import transcribe_audio_file


@app.post("/transcribe", summary="Transcribe uploaded audio")
async def transcribe_endpoint(
    audio: UploadFile = File(...),
):
    """
    - Save audio to UPLOAD_DIR_AUDIO/<uuid>.<ext>, then call transcribe_audio_file(file_path)
    - Return JSON: {status, filename, transcript: List[ {id, start, end, text} ]}
    """
    import uuid

    os.makedirs(UPLOAD_DIR_AUDIO, exist_ok=True)

    file_ext = os.path.splitext(audio.filename)[1]
    audio_id = str(uuid.uuid4())
    saved_audio = f"{audio_id}{file_ext}"
    audio_path = os.path.join(UPLOAD_DIR_AUDIO, saved_audio)

    try:
        with open(audio_path, "wb") as buf:
            buf.write(await audio.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save audio: {e}")

    try:
        transcript = transcribe_audio_file(audio_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {e}")

    return {"status": "success", "filename": saved_audio, "transcript": transcript}


from image.captioner import generate_caption


@app.post("/caption", summary="Generate a caption for an uploaded image")
async def caption_endpoint(
    image: UploadFile = File(...),
):
    """
    - Save image to UPLOAD_DIR_IMAGE/<uuid>.<ext>
    - Call generate_caption(image_path) → returns caption string
    - Return JSON: {status, filename, caption}
    """
    import uuid

    os.makedirs(UPLOAD_DIR_IMAGE, exist_ok=True)

    file_ext = os.path.splitext(image.filename)[1]
    img_id = str(uuid.uuid4())
    saved_img = f"{img_id}{file_ext}"
    img_path = os.path.join(UPLOAD_DIR_IMAGE, saved_img)

    try:
        with open(img_path, "wb") as buf:
            buf.write(await image.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save image: {e}")

    try:
        caption_text = generate_caption(img_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Captioning error: {e}")

    return {"status": "success", "filename": saved_img, "caption": caption_text}


from chart.parser import parse_chart


@app.post("/chart/parse", summary="Extract structured data from a chart image")
async def chart_parse_endpoint(
    chart: UploadFile = File(...),
):
    """
    - Save chart to UPLOAD_DIR_CHART/<uuid>.<ext>
    - Call parse_chart(image_path) → returns {"axis_labels": {...}, "series": [...]} 
    - Return JSON: {status, filename, data}
    """
    import uuid

    os.makedirs(UPLOAD_DIR_CHART, exist_ok=True)

    file_ext = os.path.splitext(chart.filename)[1]
    chart_id = str(uuid.uuid4())
    saved_chart = f"{chart_id}{file_ext}"
    chart_path = os.path.join(UPLOAD_DIR_CHART, saved_chart)

    try:
        with open(chart_path, "wb") as buf:
            buf.write(await chart.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save chart: {e}")

    try:
        parsed_data = parse_chart(chart_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart parsing error: {e}")

    return {"status": "success", "filename": saved_chart, "data": parsed_data}


from embedding.chunk_embed import embed_text, process_document
from graph.graph_builder import build_graph


@app.post("/embed-text", summary="Generate embedding for raw text")
async def embed_text_endpoint(
    text: str = Form(...),
):
    """
    - Call embed_text(text) → returns List[float]
    - Return JSON: {status, embedding: [floats...]}
    """
    try:
        vector = embed_text(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {e}")
    return {"status": "success", "embedding": vector}


@app.get("/search", summary="Semantic + graph search across all media")
def search_endpoint(
    q: str,
    limit: int = 10,
    graph_depth: int = 1,
    db: Session = Depends(get_db),
):
    """
    - Step 1: Run a semantic search in Weaviate
    - Step 2: Query Neo4j for related entities
    - Step 3: Fetch chunk metadata from PostgreSQL
    - Step 4: Build a combined JSON result
    """
    try:
        response = (
            weaviate_client.query.get(
                "Chunk", ["id", "document_id", "chunk_index", "text_content"]
            )
            .with_near_text({"concepts": [q]})
            .with_limit(limit)
            .do()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search error: {e}")

    hits = response.get("data", {}).get("Get", {}).get("Chunk", [])
    results = []

    for hit in hits:
        chunk_id = hit.get("id")
        semantic_score = hit.get("_additional", {}).get("distance", None)
        cypher_query = (
            "MATCH (c:Chunk {id: $chunk_id})-[r*1..$depth]-(n) "
            "RETURN DISTINCT n.name AS name, n.label AS label"
        )
        try:
            related = run_neo4j_read(cypher_query, {"chunk_id": chunk_id, "depth": graph_depth})
        except Exception:
            related = []

        chunk_row = db.query(Chunk).filter(Chunk.id == chunk_id).first()
        text_snippet = chunk_row.text_content if chunk_row else hit.get("text_content")

        results.append({
            "chunk_id": chunk_id,
            "document_id": hit.get("document_id"),
            "chunk_index": hit.get("chunk_index"),
            "text_content": text_snippet,
            "score": semantic_score,
            "related_entities": related,
        })

    return {"status": "success", "results": results}


@app.get("/graph/entity/{entity_name}", summary="Get graph neighbors for an entity")
def get_entity_neighbors(entity_name: str, depth: int = 1):
    cypher = (
        "MATCH (e:Entity {name: $entity_name})-[r*1..$depth]-(n) "
        "RETURN DISTINCT n.id AS node_id, labels(n) AS node_labels, n.name AS name, n.label AS label"
    )
    try:
        neighbors = run_neo4j_read(cypher, {"entity_name": entity_name, "depth": depth})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j query error: {e}")

    return {"status": "success", "neighbors": neighbors}


@app.get("/document/{document_id}/chunks", summary="List all chunks for a document")
def list_document_chunks(document_id: str, db: Session = Depends(get_db)):
    chunk_rows = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
        .all()
    )
    chunks = [
        {"chunk_id": c.id, "chunk_index": c.chunk_index, "text_content": c.text_content}
        for c in chunk_rows
    ]
    return {"status": "success", "chunks": chunks}


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)
