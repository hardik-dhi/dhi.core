#!/usr/bin/env python3
"""
Plaid API Service for Airbyte Integration

This service exposes Plaid transaction and account data through REST API endpoints
that Airbyte can consume as a custom HTTP source connector.
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dhi_core.plaid.client import (
    PlaidClient,
    PlaidAccount,
    PlaidTransaction,
    SessionLocal,
    get_user_transactions
)

app = FastAPI(title="Plaid API Service for Airbyte", version="1.0.0")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/accounts")
async def get_accounts(
    limit: int = Query(1000, description="Maximum number of accounts to return"),
    offset: int = Query(0, description="Number of accounts to skip")
):
    """
    Get all Plaid accounts in Airbyte-compatible format.
    
    Returns accounts with standardized schema that Airbyte can consume.
    """
    try:
        db = SessionLocal()
        accounts = db.query(PlaidAccount).offset(offset).limit(limit).all()
        db.close()
        
        # Transform to Airbyte-compatible format
        airbyte_accounts = []
        for account in accounts:
            airbyte_accounts.append({
                "account_id": account.id,
                "access_token": account.access_token,  # Be careful with this in production
                "item_id": account.item_id,
                "name": account.account_name,
                "type": account.account_type,
                "subtype": account.account_subtype,
                "institution_name": account.institution_name,
                "mask": account.mask,
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "updated_at": account.updated_at.isoformat() if account.updated_at else None,
                "_airbyte_extracted_at": datetime.utcnow().isoformat()
            })
        
        return {
            "data": airbyte_accounts,
            "has_more": len(airbyte_accounts) == limit,
            "total_count": len(airbyte_accounts)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching accounts: {str(e)}")

@app.get("/transactions")
async def get_transactions(
    limit: int = Query(1000, description="Maximum number of transactions to return"),
    offset: int = Query(0, description="Number of transactions to skip"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    account_id: Optional[str] = Query(None, description="Filter by account ID")
):
    """
    Get all Plaid transactions in Airbyte-compatible format.
    
    Supports pagination and filtering by date range and account.
    """
    try:
        db = SessionLocal()
        
        # Build query with filters
        query = db.query(PlaidTransaction)
        
        if account_id:
            query = query.filter(PlaidTransaction.account_id == account_id)
        
        if start_date:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(PlaidTransaction.date >= start_date_obj)
        
        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(PlaidTransaction.date <= end_date_obj)
        
        # Order by date descending for most recent first
        query = query.order_by(PlaidTransaction.date.desc())
        
        # Apply pagination
        transactions = query.offset(offset).limit(limit).all()
        db.close()
        
        # Transform to Airbyte-compatible format
        airbyte_transactions = []
        for txn in transactions:
            airbyte_transactions.append({
                "transaction_id": txn.id,
                "account_id": txn.account_id,
                "amount": float(txn.amount),
                "date": txn.date.isoformat(),
                "name": txn.name,
                "merchant_name": txn.merchant_name,
                "category": txn.category,
                "subcategory": txn.subcategory,
                "account_owner": txn.account_owner,
                "authorized_date": txn.authorized_date.isoformat() if txn.authorized_date else None,
                "location": {
                    "address": txn.location_address,
                    "city": txn.location_city,
                    "region": txn.location_region,
                    "postal_code": txn.location_postal_code,
                    "country": txn.location_country
                },
                "iso_currency_code": txn.iso_currency_code,
                "unofficial_currency_code": txn.unofficial_currency_code,
                "check_number": txn.check_number,
                "reference_number": txn.reference_number,
                "original_description": txn.original_description,
                "created_at": txn.created_at.isoformat() if txn.created_at else None,
                "updated_at": txn.updated_at.isoformat() if txn.updated_at else None,
                "_airbyte_extracted_at": datetime.utcnow().isoformat()
            })
        
        return {
            "data": airbyte_transactions,
            "has_more": len(airbyte_transactions) == limit,
            "total_count": len(airbyte_transactions)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")

@app.get("/transactions/incremental")
async def get_transactions_incremental(
    cursor_field: str = Query("updated_at", description="Field to use for incremental sync"),
    cursor_value: Optional[str] = Query(None, description="Last cursor value (ISO datetime)"),
    limit: int = Query(1000, description="Maximum number of transactions to return")
):
    """
    Get transactions for incremental sync.
    
    Uses cursor-based pagination for efficient incremental syncing.
    """
    try:
        db = SessionLocal()
        
        query = db.query(PlaidTransaction)
        
        # Apply cursor filter for incremental sync
        if cursor_value:
            if cursor_field == "updated_at":
                cursor_datetime = datetime.fromisoformat(cursor_value.replace('Z', '+00:00'))
                query = query.filter(PlaidTransaction.updated_at > cursor_datetime)
            elif cursor_field == "created_at":
                cursor_datetime = datetime.fromisoformat(cursor_value.replace('Z', '+00:00'))
                query = query.filter(PlaidTransaction.created_at > cursor_datetime)
            elif cursor_field == "date":
                cursor_date = datetime.strptime(cursor_value[:10], "%Y-%m-%d").date()
                query = query.filter(PlaidTransaction.date > cursor_date)
        
        # Order by cursor field
        if cursor_field == "updated_at":
            query = query.order_by(PlaidTransaction.updated_at.asc())
        elif cursor_field == "created_at":
            query = query.order_by(PlaidTransaction.created_at.asc())
        elif cursor_field == "date":
            query = query.order_by(PlaidTransaction.date.asc())
        
        transactions = query.limit(limit).all()
        db.close()
        
        # Transform to Airbyte-compatible format
        airbyte_transactions = []
        for txn in transactions:
            airbyte_transactions.append({
                "transaction_id": txn.id,
                "account_id": txn.account_id,
                "amount": float(txn.amount),
                "date": txn.date.isoformat(),
                "name": txn.name,
                "merchant_name": txn.merchant_name,
                "category": txn.category,
                "subcategory": txn.subcategory,
                "account_owner": txn.account_owner,
                "authorized_date": txn.authorized_date.isoformat() if txn.authorized_date else None,
                "location": {
                    "address": txn.location_address,
                    "city": txn.location_city,
                    "region": txn.location_region,
                    "postal_code": txn.location_postal_code,
                    "country": txn.location_country
                },
                "iso_currency_code": txn.iso_currency_code,
                "unofficial_currency_code": txn.unofficial_currency_code,
                "check_number": txn.check_number,
                "reference_number": txn.reference_number,
                "original_description": txn.original_description,
                "created_at": txn.created_at.isoformat() if txn.created_at else None,
                "updated_at": txn.updated_at.isoformat() if txn.updated_at else None,
                "_airbyte_extracted_at": datetime.utcnow().isoformat()
            })
        
        # Calculate next cursor value
        next_cursor = None
        if transactions:
            last_txn = transactions[-1]
            if cursor_field == "updated_at" and last_txn.updated_at:
                next_cursor = last_txn.updated_at.isoformat()
            elif cursor_field == "created_at" and last_txn.created_at:
                next_cursor = last_txn.created_at.isoformat()
            elif cursor_field == "date":
                next_cursor = last_txn.date.isoformat()
        
        return {
            "data": airbyte_transactions,
            "has_more": len(airbyte_transactions) == limit,
            "next_cursor": next_cursor
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching incremental transactions: {str(e)}")

@app.get("/schema/accounts")
async def get_accounts_schema():
    """Get the schema for accounts table for Airbyte source discovery."""
    return {
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "access_token": {"type": "string"},
            "item_id": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string"},
            "subtype": {"type": ["string", "null"]},
            "institution_name": {"type": ["string", "null"]},
            "mask": {"type": ["string", "null"]},
            "created_at": {"type": ["string", "null"], "format": "date-time"},
            "updated_at": {"type": ["string", "null"], "format": "date-time"},
            "_airbyte_extracted_at": {"type": "string", "format": "date-time"}
        },
        "required": ["account_id", "name", "type"]
    }

@app.get("/schema/transactions")
async def get_transactions_schema():
    """Get the schema for transactions table for Airbyte source discovery."""
    return {
        "type": "object",
        "properties": {
            "transaction_id": {"type": "string"},
            "account_id": {"type": "string"},
            "amount": {"type": "number"},
            "date": {"type": "string", "format": "date"},
            "name": {"type": "string"},
            "merchant_name": {"type": ["string", "null"]},
            "category": {"type": ["string", "null"]},
            "subcategory": {"type": ["string", "null"]},
            "account_owner": {"type": ["string", "null"]},
            "authorized_date": {"type": ["string", "null"], "format": "date"},
            "location": {
                "type": "object",
                "properties": {
                    "address": {"type": ["string", "null"]},
                    "city": {"type": ["string", "null"]},
                    "region": {"type": ["string", "null"]},
                    "postal_code": {"type": ["string", "null"]},
                    "country": {"type": ["string", "null"]}
                }
            },
            "iso_currency_code": {"type": ["string", "null"]},
            "unofficial_currency_code": {"type": ["string", "null"]},
            "check_number": {"type": ["string", "null"]},
            "reference_number": {"type": ["string", "null"]},
            "original_description": {"type": ["string", "null"]},
            "created_at": {"type": ["string", "null"], "format": "date-time"},
            "updated_at": {"type": ["string", "null"], "format": "date-time"},
            "_airbyte_extracted_at": {"type": "string", "format": "date-time"}
        },
        "required": ["transaction_id", "account_id", "amount", "date", "name"]
    }

@app.post("/sync/full")
async def trigger_full_sync():
    """
    Trigger a full sync of Plaid data.
    
    This endpoint can be called to refresh all Plaid data before Airbyte sync.
    """
    try:
        from dhi_core.plaid.client import fetch_transactions, SessionLocal
        
        db = SessionLocal()
        accounts = db.query(PlaidAccount).all()
        db.close()
        
        if not accounts:
            return {"message": "No accounts found to sync", "synced_accounts": 0}
        
        synced_accounts = 0
        total_transactions = 0
        
        for account in accounts:
            try:
                # Sync last 30 days of transactions
                result = fetch_transactions(account.access_token, days_back=30)
                if result['status'] == 'success':
                    synced_accounts += 1
                    total_transactions += result.get('transactions_saved', 0)
            except Exception as e:
                print(f"Error syncing account {account.id}: {e}")
                continue
        
        return {
            "message": "Full sync completed",
            "synced_accounts": synced_accounts,
            "total_accounts": len(accounts),
            "total_transactions": total_transactions
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during full sync: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get basic statistics about the Plaid data."""
    try:
        db = SessionLocal()
        
        account_count = db.query(PlaidAccount).count()
        transaction_count = db.query(PlaidTransaction).count()
        
        # Get date range of transactions
        first_transaction = db.query(PlaidTransaction).order_by(PlaidTransaction.date.asc()).first()
        last_transaction = db.query(PlaidTransaction).order_by(PlaidTransaction.date.desc()).first()
        
        db.close()
        
        return {
            "accounts": account_count,
            "transactions": transaction_count,
            "date_range": {
                "earliest": first_transaction.date.isoformat() if first_transaction else None,
                "latest": last_transaction.date.isoformat() if last_transaction else None
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

if __name__ == "__main__":
    # Start the API service
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
        log_level="info"
    )
