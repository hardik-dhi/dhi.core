#!/usr/bin/env python3
"""
Setup test data for Plaid integration testing.
"""

import sys
import os
from pathlib import Path
from datetime import date, datetime, timedelta
from decimal import Decimal

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dhi_core.plaid.client import PlaidAccount, PlaidTransaction, SessionLocal, Base, engine

def create_test_accounts():
    """Create test Plaid accounts."""
    db = SessionLocal()
    
    try:
        # Test account 1 - Checking
        account1 = PlaidAccount(
            id="test_account_1",
            access_token="access-sandbox-test-token-1",
            item_id="test_item_1",
            account_name="Test Checking Account",
            account_type="depository",
            account_subtype="checking",
            institution_name="Test Bank",
            mask="1234",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Test account 2 - Savings
        account2 = PlaidAccount(
            id="test_account_2",
            access_token="access-sandbox-test-token-2",
            item_id="test_item_2",
            account_name="Test Savings Account",
            account_type="depository",
            account_subtype="savings",
            institution_name="Test Credit Union",
            mask="5678",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Check if accounts already exist
        existing1 = db.query(PlaidAccount).filter(PlaidAccount.id == "test_account_1").first()
        existing2 = db.query(PlaidAccount).filter(PlaidAccount.id == "test_account_2").first()
        
        if not existing1:
            db.add(account1)
            print("✅ Created test checking account")
        else:
            print("ℹ️  Test checking account already exists")
            
        if not existing2:
            db.add(account2)
            print("✅ Created test savings account")
        else:
            print("ℹ️  Test savings account already exists")
        
        db.commit()
        return ["test_account_1", "test_account_2"]
        
    except Exception as e:
        print(f"❌ Error creating test accounts: {e}")
        db.rollback()
        return []
    finally:
        db.close()

def create_test_transactions(account_ids):
    """Create test transactions for the accounts."""
    db = SessionLocal()
    
    try:
        transactions = []
        base_date = date.today()
        
        # Sample transaction data
        sample_transactions = [
            {"name": "Starbucks Coffee", "amount": 4.25, "category": "Food and Drink", "merchant": "Starbucks"},
            {"name": "Grocery Store", "amount": 67.89, "category": "Shops", "merchant": "Whole Foods"},
            {"name": "Gas Station", "amount": 32.15, "category": "Transportation", "merchant": "Shell"},
            {"name": "Netflix Subscription", "amount": 15.99, "category": "Entertainment", "merchant": "Netflix"},
            {"name": "Direct Deposit", "amount": -2500.00, "category": "Deposit", "merchant": "Employer"},
            {"name": "Amazon Purchase", "amount": 89.99, "category": "Shops", "merchant": "Amazon"},
            {"name": "Restaurant", "amount": 42.33, "category": "Food and Drink", "merchant": "Local Restaurant"},
            {"name": "ATM Withdrawal", "amount": 60.00, "category": "Transfer", "merchant": "Bank ATM"},
            {"name": "Utilities", "amount": 125.50, "category": "Service", "merchant": "Electric Company"},
            {"name": "Phone Bill", "amount": 79.99, "category": "Service", "merchant": "Verizon"},
        ]
        
        transaction_count = 0
        
        for account_id in account_ids:
            for i, txn_data in enumerate(sample_transactions):
                # Create transactions for the last 30 days
                txn_date = base_date - timedelta(days=i % 30)
                txn_id = f"test_txn_{account_id}_{i}"
                
                # Check if transaction already exists
                existing = db.query(PlaidTransaction).filter(PlaidTransaction.id == txn_id).first()
                if existing:
                    continue
                
                transaction = PlaidTransaction(
                    id=txn_id,
                    account_id=account_id,
                    amount=txn_data["amount"],
                    date=txn_date,
                    name=txn_data["name"],
                    merchant_name=txn_data["merchant"],
                    category=txn_data["category"],
                    subcategory=None,
                    account_owner=None,
                    authorized_date=txn_date,
                    location_address="123 Test St",
                    location_city="Test City",
                    location_region="CA",
                    location_postal_code="12345",
                    location_country="US",
                    iso_currency_code="USD",
                    unofficial_currency_code=None,
                    check_number=None,
                    reference_number=None,
                    original_description=txn_data["name"],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                transactions.append(transaction)
                transaction_count += 1
        
        if transactions:
            db.add_all(transactions)
            db.commit()
            print(f"✅ Created {transaction_count} test transactions")
        else:
            print("ℹ️  Test transactions already exist")
        
        return transaction_count
        
    except Exception as e:
        print(f"❌ Error creating test transactions: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

def setup_test_data():
    """Set up complete test data for Plaid integration."""
    print("🔧 Setting up test data for Plaid integration...")
    
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")
    
    # Create test accounts
    account_ids = create_test_accounts()
    
    if account_ids:
        # Create test transactions
        txn_count = create_test_transactions(account_ids)
        
        print(f"\n🎉 Test data setup complete!")
        print(f"Created {len(account_ids)} test accounts")
        print(f"Created {txn_count} test transactions")
        print(f"\nYou can now test the Airbyte integration with:")
        print(f"  make airbyte-init")
    else:
        print("❌ Failed to create test accounts")

def clean_test_data():
    """Clean up test data."""
    db = SessionLocal()
    
    try:
        # Delete test transactions
        test_transactions = db.query(PlaidTransaction).filter(
            PlaidTransaction.account_id.in_(["test_account_1", "test_account_2"])
        ).all()
        
        for txn in test_transactions:
            db.delete(txn)
        
        # Delete test accounts
        test_accounts = db.query(PlaidAccount).filter(
            PlaidAccount.id.in_(["test_account_1", "test_account_2"])
        ).all()
        
        for acc in test_accounts:
            db.delete(acc)
        
        db.commit()
        print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"❌ Error cleaning test data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean_test_data()
    else:
        setup_test_data()