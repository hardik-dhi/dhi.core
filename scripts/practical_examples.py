#!/usr/bin/env python3
"""
Practical Data Consumption Examples for Plaid-Airbyte Integration
Demonstrates real-world usage scenarios for consuming bank transaction data
"""

import requests
import json
from datetime import datetime, date
from typing import Dict, List, Any

class PlaidDataConsumer:
    def __init__(self, api_url: str = "http://localhost:8080"):
        self.api_url = api_url
        
    def check_api_health(self) -> bool:
        """Check if API is available"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get overall statistics"""
        response = requests.get(f"{self.api_url}/stats")
        return response.json()
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts"""
        response = requests.get(f"{self.api_url}/accounts")
        return response.json()["data"]
    
    def get_transactions(self, limit: int = None, account_id: str = None) -> List[Dict[str, Any]]:
        """Get transactions with optional filters"""
        params = {}
        if limit:
            params["limit"] = limit
        if account_id:
            params["account_id"] = account_id
            
        response = requests.get(f"{self.api_url}/transactions", params=params)
        return response.json()["data"]

def main():
    print("🔌 PRACTICAL DATA CONSUMPTION EXAMPLES")
    print("=" * 55)
    
    consumer = PlaidDataConsumer()
    
    # Check API availability
    if not consumer.check_api_health():
        print("❌ API not available at http://localhost:8080")
        print("   Please ensure the Plaid API service is running")
        return
    
    print("✅ API Available")
    
    # Example 1: Daily Dashboard Summary
    print("\n📊 EXAMPLE 1: Daily Dashboard Summary")
    print("-" * 35)
    
    stats = consumer.get_summary_stats()
    accounts = consumer.get_accounts()
    recent_transactions = consumer.get_transactions(limit=10)
    
    print(f"📈 Portfolio Overview:")
    print(f"   • Total Accounts: {stats['accounts']}")
    print(f"   • Total Transactions: {stats['transactions']}")
    print(f"   • Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Account breakdown
    print(f"\n💳 Account Breakdown:")
    for i, account in enumerate(accounts, 1):
        balance = account.get('current_balance', 0)
        print(f"   {i}. {account['name']} ({account['type']})")
        print(f"      Institution: {account['institution_name']}")
        print(f"      Balance: ${float(balance):,.2f}")
    
    # Recent activity
    print(f"\n💰 Recent Activity (Last 10 transactions):")
    total_amount = sum(float(t['amount']) for t in recent_transactions)
    print(f"   Total Amount: ${total_amount:,.2f}")
    
    for i, transaction in enumerate(recent_transactions[:5], 1):
        amount = float(transaction['amount'])
        print(f"   {i}. ${amount:7.2f} - {transaction['name'][:30]}")
        print(f"      Date: {transaction['date']} | Category: {', '.join(transaction.get('category', ['N/A']))}")
    
    if len(recent_transactions) > 5:
        print(f"   ... and {len(recent_transactions) - 5} more transactions")
    
    # Example 2: Account-Specific Analysis
    print(f"\n🏦 EXAMPLE 2: Account-Specific Analysis")
    print("-" * 35)
    
    for account in accounts:
        account_transactions = consumer.get_transactions(account_id=account['account_id'])
        
        if account_transactions:
            account_total = sum(float(t['amount']) for t in account_transactions)
            avg_transaction = account_total / len(account_transactions)
            
            print(f"\n📋 {account['name']} Analysis:")
            print(f"   • Transaction Count: {len(account_transactions)}")
            print(f"   • Total Activity: ${account_total:,.2f}")
            print(f"   • Average Transaction: ${avg_transaction:,.2f}")
            
            # Category breakdown
            categories = {}
            for t in account_transactions:
                cat = t.get('category', ['Other'])[0] if t.get('category') else 'Other'
                categories[cat] = categories.get(cat, 0) + float(t['amount'])
            
            if categories:
                print(f"   • Top Categories:")
                for cat, amount in sorted(categories.items(), key=lambda x: abs(x[1]), reverse=True)[:3]:
                    print(f"     - {cat}: ${amount:,.2f}")
    
    # Example 3: Financial Health Indicators
    print(f"\n💡 EXAMPLE 3: Financial Health Indicators")
    print("-" * 40)
    
    all_transactions = consumer.get_transactions()
    
    if all_transactions:
        # Calculate metrics
        total_inflow = sum(float(t['amount']) for t in all_transactions if float(t['amount']) > 0)
        total_outflow = sum(float(t['amount']) for t in all_transactions if float(t['amount']) < 0)
        net_flow = total_inflow + total_outflow
        
        print(f"📊 Cash Flow Analysis:")
        print(f"   • Total Inflow:  ${total_inflow:,.2f}")
        print(f"   • Total Outflow: ${abs(total_outflow):,.2f}")
        print(f"   • Net Flow:      ${net_flow:,.2f}")
        
        # Transaction frequency
        dates = set(t['date'] for t in all_transactions)
        avg_daily_transactions = len(all_transactions) / len(dates) if dates else 0
        
        print(f"\n📅 Activity Patterns:")
        print(f"   • Unique Transaction Days: {len(dates)}")
        print(f"   • Average Daily Transactions: {avg_daily_transactions:.1f}")
        
        # Spending categories
        spending_categories = {}
        for t in all_transactions:
            if float(t['amount']) < 0:  # Outflows only
                cat = t.get('category', ['Other'])[0] if t.get('category') else 'Other'
                spending_categories[cat] = spending_categories.get(cat, 0) + abs(float(t['amount']))
        
        if spending_categories:
            print(f"\n💳 Top Spending Categories:")
            for i, (cat, amount) in enumerate(sorted(spending_categories.items(), key=lambda x: x[1], reverse=True)[:5], 1):
                print(f"   {i}. {cat}: ${amount:,.2f}")
    
    # Example 4: Data Export Simulation
    print(f"\n📤 EXAMPLE 4: Data Export Simulation")
    print("-" * 35)
    
    export_data = {
        "summary": stats,
        "accounts": accounts,
        "recent_transactions": recent_transactions,
        "export_timestamp": datetime.now().isoformat(),
        "total_records": len(all_transactions)
    }
    
    print(f"✅ Data prepared for export:")
    print(f"   • Summary stats: {len(stats)} fields")
    print(f"   • Account records: {len(accounts)}")
    print(f"   • Transaction records: {len(all_transactions)}")
    print(f"   • Export size: ~{len(json.dumps(export_data)):,} characters")
    
    # Example 5: Real-time Monitoring
    print(f"\n⚡ EXAMPLE 5: Real-time Monitoring")
    print("-" * 35)
    
    # Simulate alert conditions
    alerts = []
    
    for transaction in recent_transactions[:5]:
        amount = float(transaction['amount'])
        if abs(amount) > 1000:  # Large transaction
            alerts.append(f"Large transaction alert: ${abs(amount):,.2f} - {transaction['name']}")
        
        # Check for specific patterns
        if 'ATM' in transaction['name'].upper():
            alerts.append(f"ATM withdrawal: ${abs(amount):,.2f}")
    
    if alerts:
        print(f"🚨 Active Alerts:")
        for i, alert in enumerate(alerts, 1):
            print(f"   {i}. {alert}")
    else:
        print(f"✅ No alerts - All transactions within normal parameters")
    
    print(f"\n🎯 INTEGRATION EXAMPLES COMPLETED!")
    print(f"=" * 55)
    print(f"This data is now ready for:")
    print(f"   • Database synchronization via Airbyte")
    print(f"   • Business intelligence dashboards")
    print(f"   • Financial planning applications")
    print(f"   • Automated reporting systems")
    print(f"   • Real-time monitoring and alerts")

if __name__ == "__main__":
    main()
