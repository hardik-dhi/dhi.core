#!/usr/bin/env python3
"""
Plaid API Client - Direct Data Consumption

This demonstrates how to consume data directly from your custom Plaid API
without needing Airbyte to be fully operational.
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class PlaidAPIClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_stats(self) -> Dict:
        """Get API statistics."""
        response = self.session.get(f"{self.base_url}/stats")
        response.raise_for_status()
        return response.json()
    
    def get_accounts(self) -> List[Dict]:
        """Get all accounts."""
        response = self.session.get(f"{self.base_url}/accounts")
        response.raise_for_status()
        return response.json()["data"]
    
    def get_transactions(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all transactions."""
        url = f"{self.base_url}/transactions"
        if limit:
            url += f"?limit={limit}"
        
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()["data"]
    
    def get_incremental_transactions(self, since: Optional[str] = None) -> List[Dict]:
        """Get transactions since a specific timestamp."""
        url = f"{self.base_url}/transactions/incremental"
        if since:
            url += f"?since={since}"
        
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()["data"]
    
    def get_schema(self, table: str) -> Dict:
        """Get schema for a specific table."""
        response = self.session.get(f"{self.base_url}/schema/{table}")
        response.raise_for_status()
        return response.json()
    
    def trigger_full_sync(self) -> Dict:
        """Trigger a full sync of data."""
        response = self.session.post(f"{self.base_url}/sync/full")
        response.raise_for_status()
        return response.json()

def demo_basic_usage():
    """Demonstrate basic API usage."""
    print("🔌 Plaid API Client Demo")
    print("=" * 40)
    
    client = PlaidAPIClient()
    
    # Check health
    if not client.health_check():
        print("❌ API is not available")
        return
    
    print("✅ API is healthy")
    
    # Get stats
    stats = client.get_stats()
    print(f"📊 Stats: {stats['accounts']} accounts, {stats['transactions']} transactions")
    
    # Get accounts
    accounts = client.get_accounts()
    print(f"\n💳 Found {len(accounts)} accounts:")
    for account in accounts[:3]:  # Show first 3
        print(f"   • {account['name']} ({account['type']}) - {account['account_id']}")
    
    # Get recent transactions
    transactions = client.get_transactions(limit=5)
    print(f"\n💰 Recent {len(transactions)} transactions:")
    for txn in transactions:
        print(f"   • ${txn['amount']:.2f} - {txn['name']} ({txn['date']})")

def demo_pandas_analysis():
    """Demonstrate data analysis with pandas."""
    print("\n📊 Data Analysis with Pandas")
    print("=" * 40)
    
    client = PlaidAPIClient()
    
    # Get all data
    accounts = client.get_accounts()
    transactions = client.get_transactions()
    
    # Convert to DataFrames
    accounts_df = pd.DataFrame(accounts)
    transactions_df = pd.DataFrame(transactions)
    
    print(f"📈 Data loaded:")
    print(f"   • Accounts: {len(accounts_df)} rows")
    print(f"   • Transactions: {len(transactions_df)} rows")
    
    # Basic analysis
    print(f"\n💡 Account Summary:")
    print(accounts_df[['name', 'type', 'subtype']].to_string(index=False))
    
    print(f"\n💰 Transaction Summary:")
    print(f"   • Total amount: ${transactions_df['amount'].sum():.2f}")
    print(f"   • Average amount: ${transactions_df['amount'].mean():.2f}")
    print(f"   • Date range: {transactions_df['date'].min()} to {transactions_df['date'].max()}")
    
    # Category breakdown
    if 'category' in transactions_df.columns:
        category_totals = transactions_df.groupby('category')['amount'].sum().sort_values(ascending=False)
        print(f"\n🏷️  Top spending categories:")
        for category, amount in category_totals.head().items():
            print(f"   • {category}: ${amount:.2f}")
    
    return accounts_df, transactions_df

def demo_incremental_sync():
    """Demonstrate incremental data sync."""
    print("\n🔄 Incremental Sync Demo")
    print("=" * 40)
    
    client = PlaidAPIClient()
    
    # Get transactions from last 24 hours
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    recent_transactions = client.get_incremental_transactions(since=yesterday)
    
    print(f"📅 Transactions since {yesterday[:10]}:")
    print(f"   Found {len(recent_transactions)} recent transactions")
    
    for txn in recent_transactions[:5]:  # Show first 5
        print(f"   • ${txn['amount']:.2f} - {txn['name']} (updated: {txn['updated_at'][:19]})")

def demo_data_export():
    """Demonstrate exporting data to files."""
    print("\n💾 Data Export Demo")
    print("=" * 40)
    
    client = PlaidAPIClient()
    
    # Get data
    accounts = client.get_accounts()
    transactions = client.get_transactions()
    
    # Export to JSON
    with open('/tmp/plaid_accounts.json', 'w') as f:
        json.dump(accounts, f, indent=2, default=str)
    
    with open('/tmp/plaid_transactions.json', 'w') as f:
        json.dump(transactions, f, indent=2, default=str)
    
    # Export to CSV
    accounts_df = pd.DataFrame(accounts)
    transactions_df = pd.DataFrame(transactions)
    
    accounts_df.to_csv('/tmp/plaid_accounts.csv', index=False)
    transactions_df.to_csv('/tmp/plaid_transactions.csv', index=False)
    
    print("✅ Data exported to:")
    print("   • /tmp/plaid_accounts.json")
    print("   • /tmp/plaid_transactions.json") 
    print("   • /tmp/plaid_accounts.csv")
    print("   • /tmp/plaid_transactions.csv")

def demo_custom_etl():
    """Demonstrate a custom ETL pipeline."""
    print("\n🔧 Custom ETL Pipeline Demo")
    print("=" * 40)
    
    client = PlaidAPIClient()
    
    # Extract
    print("📥 Extracting data...")
    accounts = client.get_accounts()
    transactions = client.get_transactions()
    
    # Transform
    print("🔄 Transforming data...")
    
    # Create enriched transaction data
    enriched_transactions = []
    account_lookup = {acc['account_id']: acc for acc in accounts}
    
    for txn in transactions:
        account = account_lookup.get(txn['account_id'], {})
        enriched_txn = {
            **txn,
            'account_name': account.get('name', 'Unknown'),
            'account_type': account.get('type', 'Unknown'),
            'institution_name': account.get('institution_name', 'Unknown'),
            'amount_abs': abs(float(txn['amount'])),
            'is_debit': float(txn['amount']) > 0,
            'month': txn['date'][:7],  # YYYY-MM format
        }
        enriched_transactions.append(enriched_txn)
    
    # Load (save to file)
    print("💾 Loading data...")
    df = pd.DataFrame(enriched_transactions)
    
    # Summary report
    monthly_summary = df.groupby(['month', 'account_name']).agg({
        'amount_abs': 'sum',
        'transaction_id': 'count'
    }).round(2)
    
    print("📊 Monthly Summary by Account:")
    print(monthly_summary.to_string())
    
    # Save enriched data
    df.to_csv('/tmp/enriched_transactions.csv', index=False)
    print("\n✅ Enriched data saved to: /tmp/enriched_transactions.csv")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Plaid API Client Demo")
    parser.add_argument('--demo', choices=['basic', 'pandas', 'incremental', 'export', 'etl', 'all'], 
                       default='all', help='Which demo to run')
    
    args = parser.parse_args()
    
    if args.demo in ['basic', 'all']:
        demo_basic_usage()
    
    if args.demo in ['pandas', 'all']:
        demo_pandas_analysis()
    
    if args.demo in ['incremental', 'all']:
        demo_incremental_sync()
    
    if args.demo in ['export', 'all']:
        demo_data_export()
    
    if args.demo in ['etl', 'all']:
        demo_custom_etl()
