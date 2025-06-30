from __future__ import annotations

from datetime import date
from typing import List
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from metadata.models import init_db
from .models import Base, BankTransaction, ActionItem

# Initialize database engine and session
engine = init_db()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

# Ensure tables for domain models exist
Base.metadata.create_all(bind=engine)


def get_db():
    """Yield a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_bank_transaction(db: Session, date: date, amount: float, description: str, category: str) -> BankTransaction:
    """Create and return a new BankTransaction."""
    tx = BankTransaction(
        id=str(uuid4()),
        date=date,
        amount=amount,
        description=description,
        category=category,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def get_bank_transactions(db: Session, skip: int = 0, limit: int = 100) -> List[BankTransaction]:
    """List bank transactions with pagination."""
    return db.query(BankTransaction).offset(skip).limit(limit).all()


def create_action_item(db: Session, description: str, assigned_to: str, due_date: date, status: str, image_links: List[str], audio_links: List[str]) -> ActionItem:
    """Create and return a new ActionItem."""
    ai = ActionItem(
        id=str(uuid4()),
        description=description,
        assigned_to=assigned_to,
        due_date=due_date,
        status=status,
        image_links=image_links,
        audio_links=audio_links,
    )
    db.add(ai)
    db.commit()
    db.refresh(ai)
    return ai


def get_action_items(db: Session, skip: int = 0, limit: int = 100) -> List[ActionItem]:
    """List action items with pagination."""
    return db.query(ActionItem).offset(skip).limit(limit).all()


if __name__ == "__main__":
    # Quick test of CRUD functions
    db = next(get_db())
    print(create_bank_transaction(db, date.today(), 12.34, "Test TX", "general"))
    print(get_bank_transactions(db))
    print(create_action_item(db, "Test AI", "alice", date.today(), "open", [], []))
    print(get_action_items(db))
