#!/usr/bin/env python3
"""
Simple Plaid API Data Consumption Demo
"""

import requests
import json

def main():
    print("🔌 Plaid API Data Consumption Demo")
    print("=" * 50)
    
    base_url = "http://localhost:8080"
    
    try:
        # 1. Health Check
        print("1️⃣ Health Check:")
        health = requests.get(f"{base_url}/health", timeout=5)
        print(f"   Status: {health.json()['status']}")
        
        # 2. Get Statistics
        print("\n2️⃣ API Statistics:")
        stats = requests.get(f"{base_url}/stats", timeout=5)
        stats_data = stats.json()
        print(f"   📊 {stats_data['accounts']} accounts, {stats_data['transactions']} transactions")
        print(f"   📅 Date range: {stats_data['date_range']['earliest']} to {stats_data['date_range']['latest']}")
        
        # 3. Get Accounts
        print("\n3️⃣ Account Data:")
        accounts = requests.get(f"{base_url}/accounts", timeout=5)
        accounts_data = accounts.json()["data"]
        print(f"   Found {len(accounts_data)} accounts:")
        for i, account in enumerate(accounts_data[:3], 1):
            print(f"   {i}. {account['name']} ({account['type']}) - ID: {account['account_id']}")
        
        # 4. Get Sample Transactions
        print("\n4️⃣ Transaction Data (Latest 5):")
        transactions = requests.get(f"{base_url}/transactions?limit=5", timeout=5)
        transaction_data = transactions.json()["data"]
        print(f"   Found {len(transaction_data)} transactions:")
        for i, txn in enumerate(transaction_data, 1):
            amount = float(txn['amount'])
            print(f"   {i}. ${amount:.2f} - {txn['name']} ({txn['date']})")
        
        # 5. Get Schema Information
        print("\n5️⃣ Data Schema:")
        account_schema = requests.get(f"{base_url}/schema/accounts", timeout=5)
        transaction_schema = requests.get(f"{base_url}/schema/transactions", timeout=5)
        
        acc_props = list(account_schema.json()['properties'].keys())
        txn_props = list(transaction_schema.json()['properties'].keys())
        
        print(f"   Account fields ({len(acc_props)}): {', '.join(acc_props[:8])}...")
        print(f"   Transaction fields ({len(txn_props)}): {', '.join(txn_props[:8])}...")
        
        # 6. Data Export Examples
        print("\n6️⃣ Data Export Examples:")
        
        # Save accounts to JSON
        with open('/tmp/plaid_accounts_export.json', 'w') as f:
            json.dump(accounts_data, f, indent=2, default=str)
        print("   ✅ Accounts exported to: /tmp/plaid_accounts_export.json")
        
        # Save transactions to JSON
        all_transactions = requests.get(f"{base_url}/transactions", timeout=10)
        all_txn_data = all_transactions.json()["data"]
        
        with open('/tmp/plaid_transactions_export.json', 'w') as f:
            json.dump(all_txn_data, f, indent=2, default=str)
        print(f"   ✅ {len(all_txn_data)} transactions exported to: /tmp/plaid_transactions_export.json")
        
        # 7. Incremental Sync Demo
        print("\n7️⃣ Incremental Sync:")
        incremental = requests.get(f"{base_url}/transactions/incremental", timeout=5)
        inc_data = incremental.json()["data"]
        print(f"   📈 {len(inc_data)} transactions available for incremental sync")
        
        print("\n✅ Demo completed successfully!")
        print("\n💡 Usage Examples:")
        print("   • Use requests.get() to fetch data in your applications")
        print("   • Set up scheduled jobs to pull incremental updates")
        print("   • Export to CSV/JSON for analysis tools")
        print("   • Build dashboards using this real-time data")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
