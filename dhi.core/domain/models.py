# Requires: pip install sqlalchemy psycopg2-binary

from __future__ import annotations

from sqlalchemy import Column, String, Float, Date, Text, Enum, JSON, DateTime, func
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()


class BankTransaction(Base):
    """Record of a single bank transaction."""

    __tablename__ = "bank_transactions"

    id = Column(String, primary_key=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(512))
    category = Column(String(128))


class ActionStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class ActionItem(Base):
    """Action item generated from a document."""

    __tablename__ = "action_items"

    id = Column(String, primary_key=True)
    description = Column(Text, nullable=False)
    assigned_to = Column(String(128))
    due_date = Column(Date)
    status = Column(Enum(ActionStatus), default=ActionStatus.OPEN)
    image_links = Column(JSON, default=list)
    audio_links = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
