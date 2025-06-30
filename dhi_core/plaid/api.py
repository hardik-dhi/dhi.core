"""
FastAPI endpoints for Plaid integration.

This module provides REST API endpoints for:
1. Creating link tokens for Plaid Link
2. Exchanging public tokens for access tokens
3. Fetching transactions from linked accounts
4. Managing bank account connections
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Depends, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .client import (
    PlaidClient, 
    PlaidAccount, 
    PlaidTransaction,
    link_bank_account,
    fetch_transactions,
    get_user_transactions,
    get_db
)

router = APIRouter(prefix="/plaid", tags=["plaid"])


class LinkTokenRequest(BaseModel):
    """Request model for creating link token."""
    user_id: str
    client_name: Optional[str] = "DHI Core"


class LinkTokenResponse(BaseModel):
    """Response model for link token creation."""
    link_token: str
    expiration: str


class ExchangeTokenRequest(BaseModel):
    """Request model for exchanging public token."""
    user_id: str
    public_token: str


class AccountInfo(BaseModel):
    """Account information model."""
    account_id: str
    name: str
    type: str
    subtype: Optional[str]
    mask: Optional[str]


class ExchangeTokenResponse(BaseModel):
    """Response model for token exchange."""
    status: str
    access_token: Optional[str]
    item_id: Optional[str]
    accounts: Optional[List[AccountInfo]]
    error: Optional[str]


class FetchTransactionsRequest(BaseModel):
    """Request model for fetching transactions."""
    access_token: str
    days_back: Optional[int] = 30
    account_ids: Optional[List[str]] = None


class TransactionInfo(BaseModel):
    """Transaction information model."""
    id: str
    account_id: str
    amount: float
    date: str
    name: str
    merchant_name: Optional[str]
    category: Optional[str]
    subcategory: Optional[str]
    location: Optional[Dict[str, Any]]


class FetchTransactionsResponse(BaseModel):
    """Response model for transaction fetching."""
    status: str
    transactions_fetched: Optional[int]
    transactions_saved: Optional[int]
    date_range: Optional[Dict[str, str]]
    error: Optional[str]


class GetTransactionsResponse(BaseModel):
    """Response model for getting user transactions."""
    transactions: List[TransactionInfo]
    total_count: int


@router.post("/link-token", response_model=LinkTokenResponse)
async def create_link_token(request: LinkTokenRequest):
    """
    Create a link token for Plaid Link initialization.
    
    This endpoint creates a link token that can be used to initialize
    Plaid Link on the frontend for bank account connection.
    """
    try:
        plaid_client = PlaidClient()
        link_token = plaid_client.create_link_token(
            user_id=request.user_id,
            client_name=request.client_name
        )
        
        return LinkTokenResponse(
            link_token=link_token,
            expiration="4 hours"  # Plaid link tokens expire after 4 hours
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create link token: {str(e)}")


@router.post("/exchange-token", response_model=ExchangeTokenResponse)
async def exchange_public_token(request: ExchangeTokenRequest):
    """
    Exchange a public token for an access token and link bank account.
    
    This endpoint is called after a user successfully connects their bank
    account through Plaid Link. It exchanges the public token for an access
    token and saves the account information.
    """
    try:
        result = link_bank_account(request.user_id, request.public_token)
        
        if result['status'] == 'success':
            return ExchangeTokenResponse(
                status="success",
                access_token=result['access_token'],
                item_id=result['item_id'],
                accounts=[
                    AccountInfo(**account) for account in result['accounts']
                ]
            )
        else:
            return ExchangeTokenResponse(
                status="error",
                error=result['error']
            )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to exchange token: {str(e)}")


@router.post("/fetch-transactions", response_model=FetchTransactionsResponse)
async def fetch_transactions_endpoint(request: FetchTransactionsRequest):
    """
    Fetch transactions from Plaid for a given access token.
    
    This endpoint fetches transactions from Plaid and stores them in
    the local database. It can be used to sync recent transactions.
    """
    try:
        result = fetch_transactions(
            access_token=request.access_token,
            days_back=request.days_back,
            account_ids=request.account_ids
        )
        
        if result['status'] == 'success':
            return FetchTransactionsResponse(
                status="success",
                transactions_fetched=result['transactions_fetched'],
                transactions_saved=result['transactions_saved'],
                date_range=result['date_range']
            )
        else:
            return FetchTransactionsResponse(
                status="error",
                error=result['error']
            )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch transactions: {str(e)}")


@router.get("/transactions/{user_id}", response_model=GetTransactionsResponse)
async def get_transactions_endpoint(
    user_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get stored transactions for a user.
    
    This endpoint retrieves transactions that have been previously
    fetched and stored in the local database.
    """
    try:
        transactions = get_user_transactions(user_id, limit)
        
        return GetTransactionsResponse(
            transactions=[
                TransactionInfo(**transaction) for transaction in transactions
            ],
            total_count=len(transactions)
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get transactions: {str(e)}")


@router.get("/accounts/{user_id}")
async def get_user_accounts(user_id: str, db: Session = Depends(get_db)):
    """
    Get linked bank accounts for a user.
    
    This endpoint returns all bank accounts that have been linked
    by the user through Plaid.
    """
    try:
        # In a real application, you would filter by user_id
        accounts = db.query(PlaidAccount).all()
        
        return {
            "status": "success",
            "accounts": [
                {
                    "account_id": account.id,
                    "name": account.account_name,
                    "type": account.account_type,
                    "subtype": account.account_subtype,
                    "institution": account.institution_name,
                    "mask": account.mask,
                    "created_at": account.created_at.isoformat()
                }
                for account in accounts
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get accounts: {str(e)}")


@router.post("/sync-transactions/{access_token}")
async def sync_transactions(
    access_token: str,
    days_back: int = 7
):
    """
    Sync recent transactions for an access token.
    
    This is a convenience endpoint to quickly sync recent transactions
    for a specific access token.
    """
    try:
        result = fetch_transactions(access_token, days_back)
        
        return {
            "status": result['status'],
            "message": f"Synced {result.get('transactions_saved', 0)} new transactions",
            "details": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to sync transactions: {str(e)}")


@router.get("/transaction-summary/{user_id}")
async def get_transaction_summary(
    user_id: str,
    days_back: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get transaction summary for a user.
    
    This endpoint provides a summary of transactions including
    total spending, income, and category breakdowns.
    """
    try:
        # Get user's accounts
        accounts = db.query(PlaidAccount).all()  # Filter by user_id in real app
        
        if not accounts:
            return {
                "status": "success",
                "summary": {
                    "total_transactions": 0,
                    "total_spending": 0,
                    "total_income": 0,
                    "categories": {}
                }
            }
        
        account_ids = [acc.id for acc in accounts]
        
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        # Get transactions in date range
        transactions = db.query(PlaidTransaction).filter(
            PlaidTransaction.account_id.in_(account_ids),
            PlaidTransaction.date >= start_date,
            PlaidTransaction.date <= end_date
        ).all()
        
        # Calculate summary
        total_spending = 0
        total_income = 0
        categories = {}
        
        for txn in transactions:
            if txn.amount > 0:  # Positive amounts are typically debits (spending)
                total_spending += txn.amount
            else:  # Negative amounts are typically credits (income)
                total_income += abs(txn.amount)
            
            # Category breakdown
            category = txn.category or "Other"
            if category not in categories:
                categories[category] = {"count": 0, "amount": 0}
            categories[category]["count"] += 1
            categories[category]["amount"] += txn.amount
        
        return {
            "status": "success",
            "summary": {
                "total_transactions": len(transactions),
                "total_spending": round(total_spending, 2),
                "total_income": round(total_income, 2),
                "net_cash_flow": round(total_income - total_spending, 2),
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "categories": categories
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get transaction summary: {str(e)}")
