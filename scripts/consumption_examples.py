#!/usr/bin/env python3
"""
Practical Data Consumption Examples for Plaid API

This file demonstrates real-world scenarios for consuming your Plaid API data.
"""

import requests
import json
import csv
from datetime import datetime, timedelta
from collections import defaultdict

class PlaidDataConsumer:
    def __init__(self, api_url="http://localhost:8080"):
        self.api_url = api_url.rstrip('/')
    
    def get_data(self, endpoint, params=None):
        """Helper method to fetch data from API."""
        try:
            url = f"{self.api_url}/{endpoint}"
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {endpoint}: {e}")
            return None

# Scenario 1: Daily ETL Job
def daily_etl_example():
    """Example: Daily ETL job to process new transactions."""
    print("\n📅 SCENARIO 1: Daily ETL Job")
    print("-" * 40)
    
    consumer = PlaidDataConsumer()
    
    # Get transactions from last 24 hours
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    
    # In real usage, you'd store the last sync timestamp
    data = consumer.get_data("transactions/incremental", {"since": yesterday})
    
    if data:
        transactions = data.get("data", [])
        print(f"✅ Found {len(transactions)} new transactions since yesterday")
        
        # Process transactions (example: categorize spending)
        categories = defaultdict(float)
        for txn in transactions:
            categories[txn.get('category', 'Unknown')] += float(txn['amount'])
        
        print("📊 Spending by category:")
        for category, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"   {category}: ${amount:.2f}")

# Scenario 2: Export for Excel Analysis
def excel_export_example():
    """Example: Export data for Excel analysis."""
    print("\n📊 SCENARIO 2: Excel Export")
    print("-" * 40)
    
    consumer = PlaidDataConsumer()
    
    # Get all accounts and transactions
    accounts_data = consumer.get_data("accounts")
    transactions_data = consumer.get_data("transactions")
    
    if accounts_data and transactions_data:
        accounts = accounts_data["data"]
        transactions = transactions_data["data"]
        
        # Create account lookup
        account_names = {acc['account_id']: acc['name'] for acc in accounts}
        
        # Prepare enriched data for Excel
        excel_data = []
        for txn in transactions:
            excel_row = {
                'Date': txn['date'],
                'Account': account_names.get(txn['account_id'], 'Unknown'),
                'Description': txn['name'],
                'Category': txn.get('category', 'Uncategorized'),
                'Amount': float(txn['amount']),
                'Merchant': txn.get('merchant_name', ''),
                'Transaction_ID': txn['transaction_id']
            }
            excel_data.append(excel_row)
        
        # Save to CSV (Excel-compatible)
        filename = f"/tmp/plaid_transactions_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='') as csvfile:
            if excel_data:
                writer = csv.DictWriter(csvfile, fieldnames=excel_data[0].keys())
                writer.writeheader()
                writer.writerows(excel_data)
        
        print(f"✅ Exported {len(excel_data)} transactions to: {filename}")
        print("💡 You can now open this file in Excel for analysis")

# Scenario 3: Real-time Dashboard Data
def dashboard_data_example():
    """Example: Get summary data for a dashboard."""
    print("\n📈 SCENARIO 3: Dashboard Summary")
    print("-" * 40)
    
    consumer = PlaidDataConsumer()
    
    # Get current stats
    stats = consumer.get_data("stats")
    accounts = consumer.get_data("accounts")
    recent_transactions = consumer.get_data("transactions", {"limit": 10})
    
    if all([stats, accounts, recent_transactions]):
        print("🎯 Dashboard Metrics:")
        print(f"   Total Accounts: {stats['accounts']}")
        print(f"   Total Transactions: {stats['transactions']}")
        print(f"   Data Range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        
        # Account breakdown
        account_types = defaultdict(int)
        for acc in accounts["data"]:
            account_types[acc['type']] += 1
        
        print(f"   Account Types: {dict(account_types)}")
        
        # Recent activity
        recent = recent_transactions["data"]
        total_recent = sum(float(txn['amount']) for txn in recent)
        print(f"   Recent Activity: {len(recent)} transactions, ${total_recent:.2f}")
        
        # Latest transaction
        if recent:
            latest = recent[0]
            print(f"   Latest Transaction: ${latest['amount']} - {latest['name']} ({latest['date']})")

# Scenario 4: Automated Alerts
def alert_system_example():
    """Example: Check for unusual transactions (alert system)."""
    print("\n🚨 SCENARIO 4: Automated Alerts")
    print("-" * 40)
    
    consumer = PlaidDataConsumer()
    
    # Get recent transactions
    recent_data = consumer.get_data("transactions", {"limit": 50})
    
    if recent_data:
        transactions = recent_data["data"]
        
        # Define alert conditions
        large_transaction_threshold = 100.0
        suspicious_keywords = ['atm', 'withdrawal', 'cash advance']
        
        alerts = []
        
        for txn in transactions:
            amount = float(txn['amount'])
            name = txn['name'].lower()
            
            # Large transaction alert
            if amount > large_transaction_threshold:
                alerts.append(f"💰 Large transaction: ${amount:.2f} - {txn['name']}")
            
            # Suspicious keyword alert
            for keyword in suspicious_keywords:
                if keyword in name:
                    alerts.append(f"⚠️  Suspicious activity: {txn['name']} (${amount:.2f})")
                    break
        
        if alerts:
            print(f"🚨 Found {len(alerts)} alerts:")
            for alert in alerts[:5]:  # Show first 5
                print(f"   {alert}")
        else:
            print("✅ No alerts detected")

# Scenario 5: Data Synchronization
def sync_to_database_example():
    """Example: Sync data to your own database."""
    print("\n🔄 SCENARIO 5: Database Synchronization")
    print("-" * 40)
    
    consumer = PlaidDataConsumer()
    
    # Simulate getting last sync timestamp from your database
    # In real usage, you'd query your database for the last processed transaction
    last_sync = "2025-06-20T00:00:00"  # Example timestamp
    
    # Get incremental data
    incremental_data = consumer.get_data("transactions/incremental", {"since": last_sync})
    
    if incremental_data:
        new_transactions = incremental_data["data"]
        print(f"📥 Found {len(new_transactions)} new/updated transactions since {last_sync}")
        
        # Simulate database operations
        for txn in new_transactions[:3]:  # Show example for first 3
            print(f"   📝 Processing: {txn['transaction_id']} - ${txn['amount']} ({txn['name']})")
            # Here you would INSERT/UPDATE your database
            # INSERT INTO transactions (id, amount, name, ...) VALUES (...)
        
        if new_transactions:
            latest_update = max(txn['updated_at'] for txn in new_transactions)
            print(f"✅ Sync complete. Next sync from: {latest_update}")

# Scenario 6: Monthly Report Generation
def monthly_report_example():
    """Example: Generate monthly spending report."""
    print("\n📊 SCENARIO 6: Monthly Report")
    print("-" * 40)
    
    consumer = PlaidDataConsumer()
    
    # Get all transactions
    all_data = consumer.get_data("transactions")
    accounts_data = consumer.get_data("accounts")
    
    if all_data and accounts_data:
        transactions = all_data["data"]
        accounts = accounts_data["data"]
        account_lookup = {acc['account_id']: acc['name'] for acc in accounts}
        
        # Group by month and account
        monthly_data = defaultdict(lambda: defaultdict(float))
        
        for txn in transactions:
            month = txn['date'][:7]  # YYYY-MM
            account_name = account_lookup.get(txn['account_id'], 'Unknown')
            monthly_data[month][account_name] += float(txn['amount'])
        
        print("📅 Monthly Spending Report:")
        for month in sorted(monthly_data.keys()):
            print(f"\n   {month}:")
            month_total = 0
            for account, amount in monthly_data[month].items():
                print(f"     {account}: ${amount:.2f}")
                month_total += amount
            print(f"     TOTAL: ${month_total:.2f}")

def main():
    """Run all consumption examples."""
    print("🔌 PLAID API DATA CONSUMPTION EXAMPLES")
    print("=" * 50)
    
    # Test API availability first
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code != 200:
            print("❌ API not available")
            return
    except:
        print("❌ Cannot connect to API")
        return
    
    print("✅ API is available - running examples...")
    
    # Run all scenarios
    daily_etl_example()
    excel_export_example()
    dashboard_data_example()
    alert_system_example()
    sync_to_database_example()
    monthly_report_example()
    
    print("\n" + "=" * 50)
    print("🎉 All examples completed!")
    print("\n💡 Next Steps:")
    print("   • Adapt these patterns to your specific needs")
    print("   • Set up scheduled jobs for regular data processing")
    print("   • Build web dashboards using this API as backend")
    print("   • Integrate with your existing business systems")

if __name__ == "__main__":
    main()
