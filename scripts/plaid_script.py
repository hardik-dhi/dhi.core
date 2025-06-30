#!/usr/bin/env python3
"""
Script to interact with Plaid API to fetch bank transactions.

This script provides a command-line interface for:
1. Creating link tokens
2. Linking bank accounts
3. Fetching transactions
4. Managing Plaid integration

Usage:
    python scripts/plaid_script.py create-link-token <user_id>
    python scripts/plaid_script.py link-account <user_id> <public_token>
    python scripts/plaid_script.py fetch-transactions <access_token> [days_back]
    python scripts/plaid_script.py get-transactions <user_id> [limit]
    python scripts/plaid_script.py sync-all-accounts [days_back]
"""

import sys
import os
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dhi_core.plaid.client import (
    PlaidClient,
    link_bank_account,
    fetch_transactions,
    get_user_transactions,
    PlaidAccount,
    SessionLocal
)


def create_link_token(user_id: str, client_name: str = "DHI Core"):
    """Create a link token for Plaid Link initialization."""
    try:
        plaid_client = PlaidClient()
        link_token = plaid_client.create_link_token(user_id, client_name)
        
        print(f"✅ Link token created successfully!")
        print(f"User ID: {user_id}")
        print(f"Link Token: {link_token}")
        print(f"⚠️  This token expires in 4 hours")
        
        return link_token
    
    except Exception as e:
        print(f"❌ Error creating link token: {e}")
        return None


def link_account(user_id: str, public_token: str):
    """Link a bank account using public token from Plaid Link."""
    try:
        print(f"🔗 Linking bank account for user: {user_id}")
        result = link_bank_account(user_id, public_token)
        
        if result['status'] == 'success':
            print(f"✅ Account linked successfully!")
            print(f"Access Token: {result['access_token'][:20]}...")
            print(f"Item ID: {result['item_id']}")
            print(f"Accounts found: {len(result['accounts'])}")
            
            for account in result['accounts']:
                print(f"  - {account['name']} ({account['type']}) - *{account['mask']}")
        else:
            print(f"❌ Failed to link account: {result['error']}")
        
        return result
    
    except Exception as e:
        print(f"❌ Error linking account: {e}")
        return None


def fetch_account_transactions(access_token: str, days_back: int = 30):
    """Fetch transactions for a specific access token."""
    try:
        print(f"📥 Fetching transactions for last {days_back} days...")
        result = fetch_transactions(access_token, days_back)
        
        if result['status'] == 'success':
            print(f"✅ Transactions fetched successfully!")
            print(f"Transactions fetched: {result['transactions_fetched']}")
            print(f"New transactions saved: {result['transactions_saved']}")
            print(f"Date range: {result['date_range']['start']} to {result['date_range']['end']}")
        else:
            print(f"❌ Failed to fetch transactions: {result['error']}")
        
        return result
    
    except Exception as e:
        print(f"❌ Error fetching transactions: {e}")
        return None


def get_transactions(user_id: str, limit: int = 100):
    """Get stored transactions for a user."""
    try:
        print(f"📋 Getting transactions for user: {user_id}")
        transactions = get_user_transactions(user_id, limit)
        
        print(f"✅ Found {len(transactions)} transactions")
        
        if transactions:
            print(f"\n📊 Recent transactions:")
            print(f"{'Date':<12} {'Amount':<10} {'Name':<30} {'Category':<15}")
            print("-" * 70)
            
            for txn in transactions[:10]:  # Show first 10 transactions
                amount_str = f"${txn['amount']:,.2f}"
                category = txn['category'] or 'N/A'
                print(f"{txn['date']:<12} {amount_str:<10} {txn['name'][:28]:<30} {category[:13]:<15}")
            
            if len(transactions) > 10:
                print(f"... and {len(transactions) - 10} more transactions")
        
        return transactions
    
    except Exception as e:
        print(f"❌ Error getting transactions: {e}")
        return None


def sync_all_accounts(days_back: int = 7):
    """Sync transactions for all linked accounts."""
    try:
        db = SessionLocal()
        accounts = db.query(PlaidAccount).all()
        db.close()
        
        if not accounts:
            print("❌ No linked accounts found")
            return
        
        print(f"🔄 Syncing transactions for {len(accounts)} accounts...")
        
        total_fetched = 0
        total_saved = 0
        
        for account in accounts:
            print(f"  Syncing {account.account_name} ({account.mask})...")
            result = fetch_transactions(account.access_token, days_back)
            
            if result['status'] == 'success':
                fetched = result['transactions_fetched']
                saved = result['transactions_saved']
                total_fetched += fetched
                total_saved += saved
                print(f"    ✅ {fetched} fetched, {saved} new")
            else:
                print(f"    ❌ Error: {result['error']}")
        
        print(f"\n✅ Sync complete!")
        print(f"Total transactions fetched: {total_fetched}")
        print(f"Total new transactions saved: {total_saved}")
    
    except Exception as e:
        print(f"❌ Error syncing accounts: {e}")


def list_accounts():
    """List all linked bank accounts."""
    try:
        db = SessionLocal()
        accounts = db.query(PlaidAccount).all()
        db.close()
        
        if not accounts:
            print("❌ No linked accounts found")
            return
        
        print(f"🏦 Found {len(accounts)} linked accounts:")
        print(f"{'Name':<30} {'Type':<15} {'Institution':<20} {'Mask':<8} {'Created':<12}")
        print("-" * 90)
        
        for account in accounts:
            created = account.created_at.strftime("%Y-%m-%d") if account.created_at else 'N/A'
            institution = account.institution_name or 'N/A'
            print(f"{account.account_name[:28]:<30} {account.account_type:<15} {institution[:18]:<20} *{account.mask or 'N/A':<7} {created:<12}")
    
    except Exception as e:
        print(f"❌ Error listing accounts: {e}")


def transaction_summary(user_id: str, days_back: int = 30):
    """Show transaction summary for a user."""
    try:
        transactions = get_user_transactions(user_id, 1000)  # Get more transactions for summary
        
        if not transactions:
            print(f"❌ No transactions found for user: {user_id}")
            return
        
        from datetime import date, timedelta
        from collections import defaultdict
        
        # Filter transactions by date
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        filtered_transactions = [
            txn for txn in transactions 
            if start_date <= date.fromisoformat(txn['date']) <= end_date
        ]
        
        if not filtered_transactions:
            print(f"❌ No transactions found in the last {days_back} days")
            return
        
        # Calculate summary
        total_spending = sum(txn['amount'] for txn in filtered_transactions if txn['amount'] > 0)
        total_income = sum(abs(txn['amount']) for txn in filtered_transactions if txn['amount'] < 0)
        
        # Category breakdown
        categories = defaultdict(lambda: {'count': 0, 'amount': 0})
        for txn in filtered_transactions:
            category = txn['category'] or 'Other'
            categories[category]['count'] += 1
            categories[category]['amount'] += txn['amount']
        
        print(f"📊 Transaction Summary (Last {days_back} days)")
        print(f"Period: {start_date} to {end_date}")
        print(f"Total Transactions: {len(filtered_transactions)}")
        print(f"Total Spending: ${total_spending:,.2f}")
        print(f"Total Income: ${total_income:,.2f}")
        print(f"Net Cash Flow: ${total_income - total_spending:,.2f}")
        
        print(f"\n📈 Top Categories:")
        sorted_categories = sorted(categories.items(), key=lambda x: abs(x[1]['amount']), reverse=True)
        for category, data in sorted_categories[:10]:
            print(f"  {category}: {data['count']} transactions, ${abs(data['amount']):,.2f}")
    
    except Exception as e:
        print(f"❌ Error generating summary: {e}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Plaid API Integration Script")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create link token
    link_parser = subparsers.add_parser('create-link-token', help='Create a link token')
    link_parser.add_argument('user_id', help='User ID')
    link_parser.add_argument('--client-name', default='DHI Core', help='Client name')
    
    # Link account
    account_parser = subparsers.add_parser('link-account', help='Link a bank account')
    account_parser.add_argument('user_id', help='User ID')
    account_parser.add_argument('public_token', help='Public token from Plaid Link')
    
    # Fetch transactions
    fetch_parser = subparsers.add_parser('fetch-transactions', help='Fetch transactions')
    fetch_parser.add_argument('access_token', help='Access token')
    fetch_parser.add_argument('--days-back', type=int, default=30, help='Days to fetch back')
    
    # Get transactions
    get_parser = subparsers.add_parser('get-transactions', help='Get stored transactions')
    get_parser.add_argument('user_id', help='User ID')
    get_parser.add_argument('--limit', type=int, default=100, help='Maximum number of transactions')
    
    # Sync all accounts
    sync_parser = subparsers.add_parser('sync-all', help='Sync all linked accounts')
    sync_parser.add_argument('--days-back', type=int, default=7, help='Days to sync back')
    
    # List accounts
    subparsers.add_parser('list-accounts', help='List all linked accounts')
    
    # Transaction summary
    summary_parser = subparsers.add_parser('summary', help='Show transaction summary')
    summary_parser.add_argument('user_id', help='User ID')
    summary_parser.add_argument('--days-back', type=int, default=30, help='Days to analyze')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🏦 DHI Core - Plaid Integration Script")
    print("=" * 40)
    
    if args.command == 'create-link-token':
        create_link_token(args.user_id, args.client_name)
    
    elif args.command == 'link-account':
        link_account(args.user_id, args.public_token)
    
    elif args.command == 'fetch-transactions':
        fetch_account_transactions(args.access_token, args.days_back)
    
    elif args.command == 'get-transactions':
        get_transactions(args.user_id, args.limit)
    
    elif args.command == 'sync-all':
        sync_all_accounts(args.days_back)
    
    elif args.command == 'list-accounts':
        list_accounts()
    
    elif args.command == 'summary':
        transaction_summary(args.user_id, args.days_back)
    
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()


if __name__ == "__main__":
    main()
