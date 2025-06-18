# Requires: pip install python-dotenv plaid-python sqlalchemy psycopg2-binary
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseSettings
from plaid import Client

from metadata.models import SessionLocal  # type: ignore
from domain.models import BankTransaction


class Settings(BaseSettings):
    """Load Plaid API settings from .env or environment variables."""

    PLAID_CLIENT_ID: str
    PLAID_SECRET: str
    PLAID_ENV: str
    PLAID_PRODUCTS: str | None = None
    PLAID_COUNTRY_CODES: str | None = None

    class Config:
        env_file = Path(__file__).resolve().parents[1] / ".env"
        env_file_encoding = "utf-8"


load_dotenv(Settings.Config.env_file)
settings = Settings()

client = Client(
    client_id=settings.PLAID_CLIENT_ID,
    secret=settings.PLAID_SECRET,
    environment=settings.PLAID_ENV,
    api_version="2019-05-29",
)


def get_access_token(public_token: str) -> str:
    """Exchange a public_token for an access_token."""
    response = client.Item.public_token.exchange(public_token)
    return response["access_token"]


def fetch_transactions(access_token: str, start_date: str, end_date: str) -> List[dict]:
    """Fetch all transactions within the given date range."""
    all_transactions: List[dict] = []
    offset = 0
    total_transactions = None
    while total_transactions is None or len(all_transactions) < total_transactions:
        response = client.Transactions.get(
            access_token,
            start_date,
            end_date,
            options={"count": 500, "offset": offset},
        )
        transactions = response["transactions"]
        all_transactions.extend(transactions)
        total_transactions = response["total_transactions"]
        offset += len(transactions)
    return all_transactions


def store_transactions(transactions: List[dict]) -> None:
    """Persist transactions to the database."""
    db = SessionLocal()
    try:
        for transaction in transactions:
            tx = BankTransaction(
                id=str(uuid4()),
                date=datetime.strptime(transaction["date"], "%Y-%m-%d").date(),
                amount=transaction["amount"],
                description=transaction["name"],
                category=(transaction["category"][0] if transaction.get("category") else "uncategorized"),
            )
            db.add(tx)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--public-token", help="Plaid public_token", required=True)
    parser.add_argument("--start-date", help="YYYY-MM-DD", required=True)
    parser.add_argument("--end-date", help="YYYY-MM-DD", required=True)
    args = parser.parse_args()

    token = get_access_token(args.public_token)
    txs = fetch_transactions(token, args.start_date, args.end_date)
    store_transactions(txs)
    print(f"Imported {len(txs)} transactions.")
