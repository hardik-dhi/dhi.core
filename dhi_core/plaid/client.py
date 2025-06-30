"""
Plaid API integration for fetching bank transactions.

This module provides functionality to:
1. Initialize Plaid client
2. Create link tokens for bank account linking
3. Exchange public tokens for access tokens
4. Fetch transactions from linked accounts
5. Store transactions in the database
"""

from __future__ import annotations

import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, Column, String, Float, Date, DateTime, func, Text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.api import plaid_api
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
import plaid


# Load environment variables
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class PlaidSettings(BaseSettings):
    """Plaid API configuration settings."""
    
    PLAID_CLIENT_ID: str
    PLAID_SECRET: str
    PLAID_ENVIRONMENT: str = "sandbox"  # sandbox, development, production
    PLAID_PRODUCTS: str = "transactions"
    PLAID_COUNTRY_CODES: str = "US"
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    class Config:
        env_file = Path(__file__).resolve().parents[1] / ".env"
        env_file_encoding = "utf-8"


settings = PlaidSettings()

# Database setup
Base = declarative_base()


class PlaidAccount(Base):
    """Plaid account information."""
    
    __tablename__ = "plaid_accounts"
    
    id = Column(String, primary_key=True)  # Plaid account_id
    access_token = Column(String, nullable=False)
    item_id = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    account_subtype = Column(String)
    institution_name = Column(String)
    mask = Column(String)  # Last 4 digits of account
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PlaidTransaction(Base):
    """Plaid transaction record."""
    
    __tablename__ = "plaid_transactions"
    
    id = Column(String, primary_key=True)  # Plaid transaction_id
    account_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    name = Column(String, nullable=False)
    merchant_name = Column(String)
    category = Column(String)
    subcategory = Column(String)
    account_owner = Column(String)
    authorized_date = Column(Date)
    location_address = Column(String)
    location_city = Column(String)
    location_region = Column(String)
    location_postal_code = Column(String)
    location_country = Column(String)
    iso_currency_code = Column(String)
    unofficial_currency_code = Column(String)
    check_number = Column(String)
    reference_number = Column(String)
    original_description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


def get_database_url(settings: PlaidSettings) -> str:
    """Construct the PostgreSQL database URL."""
    return (
        f"postgresql://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


# Initialize database
engine = create_engine(get_database_url(settings), future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
Base.metadata.create_all(bind=engine)


class PlaidClient:
    """Plaid API client wrapper."""
    
    def __init__(self):
        """Initialize Plaid client with configuration."""
        self.settings = settings
        
        # Configure Plaid environment
        if settings.PLAID_ENVIRONMENT == "sandbox":
            host = plaid.Environment.sandbox
        elif settings.PLAID_ENVIRONMENT == "development":
            host = plaid.Environment.development
        elif settings.PLAID_ENVIRONMENT == "production":
            host = plaid.Environment.production
        else:
            raise ValueError(f"Invalid Plaid environment: {settings.PLAID_ENVIRONMENT}")
        
        configuration = Configuration(
            host=host,
            api_key={
                'clientId': settings.PLAID_CLIENT_ID,
                'secret': settings.PLAID_SECRET,
            }
        )
        
        api_client = ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)
    
    def create_link_token(self, user_id: str, client_name: str = "DHI Core") -> str:
        """Create a link token for Plaid Link initialization."""
        try:
            products = [getattr(Products, p.strip()) for p in settings.PLAID_PRODUCTS.split(',')]
            country_codes = [getattr(CountryCode, c.strip()) for c in settings.PLAID_COUNTRY_CODES.split(',')]
            
            request = LinkTokenCreateRequest(
                products=products,
                client_name=client_name,
                country_codes=country_codes,
                language='en',
                user=LinkTokenCreateRequestUser(client_user_id=user_id)
            )
            
            response = self.client.link_token_create(request)
            return response['link_token']
        
        except Exception as e:
            raise Exception(f"Failed to create link token: {str(e)}")
    
    def exchange_public_token(self, public_token: str) -> Dict[str, str]:
        """Exchange public token for access token."""
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            
            return {
                'access_token': response['access_token'],
                'item_id': response['item_id']
            }
        
        except Exception as e:
            raise Exception(f"Failed to exchange public token: {str(e)}")
    
    def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Get account information for an access token."""
        try:
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)
            
            accounts = []
            for account in response['accounts']:
                accounts.append({
                    'account_id': account['account_id'],
                    'name': account['name'],
                    'type': account['type'],
                    'subtype': account['subtype'],
                    'mask': account['mask'],
                    'balances': {
                        'available': account['balances']['available'],
                        'current': account['balances']['current'],
                        'limit': account['balances']['limit'],
                        'iso_currency_code': account['balances']['iso_currency_code']
                    }
                })
            
            institution_name = response.get('item', {}).get('institution_id', 'Unknown')
            return accounts, institution_name
        
        except Exception as e:
            raise Exception(f"Failed to get accounts: {str(e)}")
    
    def get_transactions(
        self, 
        access_token: str, 
        start_date: date, 
        end_date: date,
        account_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get transactions for specified date range."""
        try:
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                account_ids=account_ids
            )
            
            response = self.client.transactions_get(request)
            transactions = []
            
            for txn in response['transactions']:
                location = txn.get('location', {})
                transactions.append({
                    'transaction_id': txn['transaction_id'],
                    'account_id': txn['account_id'],
                    'amount': txn['amount'],
                    'date': txn['date'],
                    'name': txn['name'],
                    'merchant_name': txn.get('merchant_name'),
                    'category': txn['category'][0] if txn.get('category') else None,
                    'subcategory': txn['category'][1] if len(txn.get('category', [])) > 1 else None,
                    'account_owner': txn.get('account_owner'),
                    'authorized_date': txn.get('authorized_date'),
                    'location_address': location.get('address'),
                    'location_city': location.get('city'),
                    'location_region': location.get('region'),
                    'location_postal_code': location.get('postal_code'),
                    'location_country': location.get('country'),
                    'iso_currency_code': txn.get('iso_currency_code'),
                    'unofficial_currency_code': txn.get('unofficial_currency_code'),
                    'check_number': txn.get('check_number'),
                    'reference_number': txn.get('reference_number'),
                    'original_description': txn.get('original_description')
                })
            
            return transactions
        
        except Exception as e:
            raise Exception(f"Failed to get transactions: {str(e)}")


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_account(db: Session, access_token: str, account_data: Dict[str, Any], institution_name: str) -> PlaidAccount:
    """Save account information to database."""
    account = PlaidAccount(
        id=account_data['account_id'],
        access_token=access_token,
        item_id=account_data.get('item_id', ''),
        account_name=account_data['name'],
        account_type=account_data['type'],
        account_subtype=account_data.get('subtype'),
        institution_name=institution_name,
        mask=account_data.get('mask')
    )
    
    # Check if account already exists
    existing = db.query(PlaidAccount).filter(PlaidAccount.id == account.id).first()
    if existing:
        # Update existing account
        for key, value in account_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        db.commit()
        return existing
    else:
        # Create new account
        db.add(account)
        db.commit()
        db.refresh(account)
        return account


def save_transactions(db: Session, transactions: List[Dict[str, Any]]) -> int:
    """Save transactions to database."""
    saved_count = 0
    
    for txn_data in transactions:
        # Check if transaction already exists
        existing = db.query(PlaidTransaction).filter(
            PlaidTransaction.id == txn_data['transaction_id']
        ).first()
        
        if not existing:
            transaction = PlaidTransaction(
                id=txn_data['transaction_id'],
                account_id=txn_data['account_id'],
                amount=txn_data['amount'],
                date=txn_data['date'],
                name=txn_data['name'],
                merchant_name=txn_data.get('merchant_name'),
                category=txn_data.get('category'),
                subcategory=txn_data.get('subcategory'),
                account_owner=txn_data.get('account_owner'),
                authorized_date=txn_data.get('authorized_date'),
                location_address=txn_data.get('location_address'),
                location_city=txn_data.get('location_city'),
                location_region=txn_data.get('location_region'),
                location_postal_code=txn_data.get('location_postal_code'),
                location_country=txn_data.get('location_country'),
                iso_currency_code=txn_data.get('iso_currency_code'),
                unofficial_currency_code=txn_data.get('unofficial_currency_code'),
                check_number=txn_data.get('check_number'),
                reference_number=txn_data.get('reference_number'),
                original_description=txn_data.get('original_description')
            )
            
            db.add(transaction)
            saved_count += 1
    
    db.commit()
    return saved_count


def link_bank_account(user_id: str, public_token: str) -> Dict[str, Any]:
    """Complete bank account linking process."""
    plaid_client = PlaidClient()
    db = next(get_db())
    
    try:
        # Exchange public token for access token
        token_data = plaid_client.exchange_public_token(public_token)
        access_token = token_data['access_token']
        item_id = token_data['item_id']
        
        # Get account information
        accounts, institution_name = plaid_client.get_accounts(access_token)
        
        # Save accounts to database
        saved_accounts = []
        for account_data in accounts:
            account_data['item_id'] = item_id
            saved_account = save_account(db, access_token, account_data, institution_name)
            saved_accounts.append(saved_account)
        
        return {
            'status': 'success',
            'access_token': access_token,
            'item_id': item_id,
            'accounts': [
                {
                    'account_id': acc.id,
                    'name': acc.account_name,
                    'type': acc.account_type,
                    'subtype': acc.account_subtype,
                    'mask': acc.mask
                }
                for acc in saved_accounts
            ]
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
    
    finally:
        db.close()


def fetch_transactions(
    access_token: str, 
    days_back: int = 30,
    account_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Fetch transactions for a given access token."""
    plaid_client = PlaidClient()
    db = next(get_db())
    
    try:
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        # Get transactions from Plaid
        transactions = plaid_client.get_transactions(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            account_ids=account_ids
        )
        
        # Save transactions to database
        saved_count = save_transactions(db, transactions)
        
        return {
            'status': 'success',
            'transactions_fetched': len(transactions),
            'transactions_saved': saved_count,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
    
    finally:
        db.close()


def get_user_transactions(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get transactions for a specific user."""
    db = next(get_db())
    
    try:
        # Get user's accounts
        accounts = db.query(PlaidAccount).all()  # In a real app, filter by user_id
        
        if not accounts:
            return []
        
        account_ids = [acc.id for acc in accounts]
        
        # Get transactions for user's accounts
        transactions = db.query(PlaidTransaction).filter(
            PlaidTransaction.account_id.in_(account_ids)
        ).order_by(PlaidTransaction.date.desc()).limit(limit).all()
        
        return [
            {
                'id': txn.id,
                'account_id': txn.account_id,
                'amount': txn.amount,
                'date': txn.date.isoformat(),
                'name': txn.name,
                'merchant_name': txn.merchant_name,
                'category': txn.category,
                'subcategory': txn.subcategory,
                'location': {
                    'address': txn.location_address,
                    'city': txn.location_city,
                    'region': txn.location_region,
                    'postal_code': txn.location_postal_code,
                    'country': txn.location_country
                }
            }
            for txn in transactions
        ]
    
    finally:
        db.close()


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python plaid_client.py create_link_token <user_id>")
        print("  python plaid_client.py link_account <user_id> <public_token>")
        print("  python plaid_client.py fetch_transactions <access_token> [days_back]")
        print("  python plaid_client.py get_transactions <user_id> [limit]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create_link_token":
        if len(sys.argv) < 3:
            print("Usage: python plaid_client.py create_link_token <user_id>")
            sys.exit(1)
        
        user_id = sys.argv[2]
        plaid_client = PlaidClient()
        
        try:
            link_token = plaid_client.create_link_token(user_id)
            print(f"Link token created: {link_token}")
        except Exception as e:
            print(f"Error creating link token: {e}")
    
    elif command == "link_account":
        if len(sys.argv) < 4:
            print("Usage: python plaid_client.py link_account <user_id> <public_token>")
            sys.exit(1)
        
        user_id = sys.argv[2]
        public_token = sys.argv[3]
        
        result = link_bank_account(user_id, public_token)
        print(f"Account linking result: {result}")
    
    elif command == "fetch_transactions":
        if len(sys.argv) < 3:
            print("Usage: python plaid_client.py fetch_transactions <access_token> [days_back]")
            sys.exit(1)
        
        access_token = sys.argv[2]
        days_back = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        
        result = fetch_transactions(access_token, days_back)
        print(f"Transaction fetch result: {result}")
    
    elif command == "get_transactions":
        if len(sys.argv) < 3:
            print("Usage: python plaid_client.py get_transactions <user_id> [limit]")
            sys.exit(1)
        
        user_id = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        
        transactions = get_user_transactions(user_id, limit)
        print(f"Found {len(transactions)} transactions")
        for txn in transactions[:5]:  # Show first 5 transactions
            print(f"  {txn['date']}: {txn['name']} - ${txn['amount']}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
