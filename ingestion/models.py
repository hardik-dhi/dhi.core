from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Document(Base):
    """SQLAlchemy ORM model for uploaded documents."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    media_type = Column(String, default="unknown", nullable=False)
