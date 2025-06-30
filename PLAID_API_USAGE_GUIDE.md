# Plaid API Data Consumption Guide

## 🎯 Quick Start

Your Plaid API is running at: **http://localhost:8080**

### Available Endpoints:
- `GET /health` - API health check
- `GET /stats` - Summary statistics
- `GET /accounts` - All accounts
- `GET /transactions` - All transactions
- `GET /transactions?limit=N` - Limited transactions
- `GET /transactions/incremental?since=TIMESTAMP` - Incremental sync
- `GET /schema/accounts` - Account schema
- `GET /schema/transactions` - Transaction schema
- `POST /sync/full` - Trigger full sync

## 📊 Data Format

### Account Data Structure:
```json
{
  "account_id": "test_account_1",
  "name": "Test Checking Account",
  "type": "depository",
  "subtype": "checking",
  "institution_name": "Test Bank",
  "mask": "1234",
  "created_at": "2025-06-24T23:26:07.494835+00:00",
  "updated_at": "2025-06-24T23:26:07.494837+00:00",
  "_airbyte_extracted_at": "2025-06-25T08:10:52.295068"
}
```

### Transaction Data Structure:
```json
{
  "transaction_id": "test_txn_test_account_1_0",
  "account_id": "test_account_1",
  "amount": 4.25,
  "date": "2025-06-24",
  "name": "Starbucks Coffee",
  "merchant_name": "Starbucks",
  "category": "Food and Drink",
  "location": {
    "address": "123 Test St",
    "city": "Test City",
    "region": "CA"
  },
  "iso_currency_code": "USD",
  "created_at": "2025-06-24T23:26:07.510595+00:00",
  "updated_at": "2025-06-24T23:26:07.510596+00:00",
  "_airbyte_extracted_at": "2025-06-25T08:10:59.924827"
}
```

## 🔌 Integration Examples

### 1. Python Integration
```python
import requests

# Basic setup
api_url = "http://localhost:8080"

# Get all accounts
response = requests.get(f"{api_url}/accounts")
accounts = response.json()["data"]

# Get recent transactions
response = requests.get(f"{api_url}/transactions?limit=10")
transactions = response.json()["data"]

# Incremental sync (get new data since timestamp)
from datetime import datetime, timedelta
yesterday = (datetime.now() - timedelta(days=1)).isoformat()
response = requests.get(f"{api_url}/transactions/incremental?since={yesterday}")
new_transactions = response.json()["data"]
```

### 2. JavaScript/Node.js Integration
```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8080';

// Get accounts
async function getAccounts() {
  const response = await axios.get(`${API_URL}/accounts`);
  return response.data.data;
}

// Get transactions
async function getTransactions(limit = null) {
  const url = limit ? `${API_URL}/transactions?limit=${limit}` : `${API_URL}/transactions`;
  const response = await axios.get(url);
  return response.data.data;
}

// Incremental sync
async function getIncrementalTransactions(since) {
  const response = await axios.get(`${API_URL}/transactions/incremental?since=${since}`);
  return response.data.data;
}
```

### 3. Bash/Shell Scripts
```bash
#!/bin/bash
API_URL="http://localhost:8080"

# Get account count
echo "Accounts: $(curl -s $API_URL/stats | jq .accounts)"

# Export transactions to CSV
curl -s $API_URL/transactions | jq -r '.data[] | [.date, .name, .amount, .category] | @csv' > transactions.csv

# Get transactions from last week
LAST_WEEK=$(date -d '7 days ago' --iso-8601)
curl -s "$API_URL/transactions/incremental?since=${LAST_WEEK}T00:00:00" | jq '.data | length'
```

### 4. SQL-like Querying (using jq)
```bash
# Top 5 largest transactions
curl -s $API_URL/transactions | jq '.data | sort_by(-.amount | tonumber) | .[0:5]'

# Transactions by category
curl -s $API_URL/transactions | jq '.data | group_by(.category) | map({category: .[0].category, count: length, total: map(.amount | tonumber) | add})'

# Transactions for specific account
curl -s $API_URL/transactions | jq '.data | map(select(.account_id == "test_account_1"))'
```

## 🔄 Automated Data Processing

### Daily ETL Script
```python
#!/usr/bin/env python3
import requests
import sqlite3
from datetime import datetime, timedelta

def daily_etl():
    api_url = "http://localhost:8080"
    
    # Get last processed timestamp from your database
    # This is just an example - replace with your actual logic
    last_sync = get_last_sync_timestamp()
    
    # Get incremental data
    response = requests.get(f"{api_url}/transactions/incremental?since={last_sync}")
    new_transactions = response.json()["data"]
    
    # Process and store in your database
    for txn in new_transactions:
        # Your processing logic here
        store_transaction(txn)
    
    # Update last sync timestamp
    if new_transactions:
        latest_update = max(txn['updated_at'] for txn in new_transactions)
        update_last_sync_timestamp(latest_update)

def get_last_sync_timestamp():
    # Implement your logic to get last sync timestamp
    return (datetime.now() - timedelta(days=1)).isoformat()

def store_transaction(txn):
    # Implement your storage logic
    print(f"Storing: {txn['transaction_id']} - ${txn['amount']}")

def update_last_sync_timestamp(timestamp):
    # Implement your logic to store last sync timestamp
    print(f"Updated last sync to: {timestamp}")

if __name__ == "__main__":
    daily_etl()
```

### Systemd Timer for Scheduled Sync
```ini
# /etc/systemd/system/plaid-sync.service
[Unit]
Description=Plaid Data Sync
After=network.target

[Service]
Type=oneshot
User=your-user
ExecStart=/usr/bin/python3 /path/to/your/daily_etl.py
WorkingDirectory=/path/to/your/project

# /etc/systemd/system/plaid-sync.timer
[Unit]
Description=Run Plaid sync every hour
Requires=plaid-sync.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

## 📈 Dashboard Integration

### Simple Flask Dashboard
```python
from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)
API_URL = "http://localhost:8080"

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/stats')
def get_stats():
    response = requests.get(f"{API_URL}/stats")
    return jsonify(response.json())

@app.route('/api/recent-transactions')
def get_recent_transactions():
    response = requests.get(f"{API_URL}/transactions?limit=10")
    return jsonify(response.json())

@app.route('/api/accounts')
def get_accounts():
    response = requests.get(f"{API_URL}/accounts")
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(debug=True)
```

## 🔍 Data Analysis Examples

### Pandas Analysis
```python
import pandas as pd
import requests

# Load data
api_url = "http://localhost:8080"
accounts_data = requests.get(f"{api_url}/accounts").json()["data"]
transactions_data = requests.get(f"{api_url}/transactions").json()["data"]

# Create DataFrames
accounts_df = pd.DataFrame(accounts_data)
transactions_df = pd.DataFrame(transactions_data)

# Analysis examples
print("Account Summary:")
print(accounts_df[['name', 'type', 'institution_name']])

print("\nTransaction Summary:")
transactions_df['amount'] = pd.to_numeric(transactions_df['amount'])
transactions_df['date'] = pd.to_datetime(transactions_df['date'])

# Monthly spending
monthly_spending = transactions_df.groupby(transactions_df['date'].dt.to_period('M'))['amount'].sum()
print("\nMonthly Spending:")
print(monthly_spending)

# Category breakdown
category_spending = transactions_df.groupby('category')['amount'].sum().sort_values(ascending=False)
print("\nSpending by Category:")
print(category_spending)
```

## 🚨 Alerting System

### Simple Alert Script
```python
import requests
import smtplib
from email.mime.text import MIMEText

def check_alerts():
    api_url = "http://localhost:8080"
    response = requests.get(f"{api_url}/transactions?limit=50")
    transactions = response.json()["data"]
    
    alerts = []
    
    for txn in transactions:
        amount = float(txn['amount'])
        
        # Large transaction alert
        if amount > 500:
            alerts.append(f"Large transaction: ${amount:.2f} - {txn['name']}")
        
        # Suspicious keywords
        if any(word in txn['name'].lower() for word in ['atm', 'cash advance']):
            alerts.append(f"Suspicious activity: {txn['name']} (${amount:.2f})")
    
    if alerts:
        send_alert_email(alerts)

def send_alert_email(alerts):
    # Configure your email settings
    msg = MIMEText('\n'.join(alerts))
    msg['Subject'] = 'Plaid Transaction Alerts'
    msg['From'] = 'alerts@yourcompany.com'
    msg['To'] = 'admin@yourcompany.com'
    
    # Send email (configure SMTP settings)
    # smtp_server.sendmail(msg['From'], [msg['To']], msg.as_string())

if __name__ == "__main__":
    check_alerts()
```

## 📊 Excel/Google Sheets Integration

### Export for Excel
```python
import pandas as pd
import requests
from datetime import datetime

def export_to_excel():
    api_url = "http://localhost:8080"
    
    # Get data
    accounts = requests.get(f"{api_url}/accounts").json()["data"]
    transactions = requests.get(f"{api_url}/transactions").json()["data"]
    
    # Create account lookup
    account_names = {acc['account_id']: acc['name'] for acc in accounts}
    
    # Enhance transaction data
    for txn in transactions:
        txn['account_name'] = account_names.get(txn['account_id'], 'Unknown')
        txn['amount'] = float(txn['amount'])
    
    # Convert to DataFrame
    df = pd.DataFrame(transactions)
    
    # Select and reorder columns for Excel
    excel_columns = ['date', 'account_name', 'name', 'category', 'amount', 'merchant_name']
    df_excel = df[excel_columns]
    
    # Export to Excel
    filename = f"plaid_transactions_{datetime.now().strftime('%Y%m%d')}.xlsx"
    df_excel.to_excel(filename, index=False, sheet_name='Transactions')
    
    print(f"Exported to: {filename}")

if __name__ == "__main__":
    export_to_excel()
```

## 🔧 Troubleshooting

### Health Check Script
```python
import requests

def health_check():
    api_url = "http://localhost:8080"
    
    try:
        # Check API health
        health_response = requests.get(f"{api_url}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ API is healthy")
            
            # Check data availability
            stats = requests.get(f"{api_url}/stats").json()
            print(f"📊 {stats['accounts']} accounts, {stats['transactions']} transactions")
            
            return True
        else:
            print(f"❌ API returned status: {health_response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is it running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    health_check()
```

## 🎯 Next Steps

1. **Choose your integration method** based on your tech stack
2. **Set up scheduled data pulls** using cron or systemd timers
3. **Build monitoring** to ensure data freshness
4. **Create dashboards** using your preferred visualization tool
5. **Set up alerts** for important transaction patterns

Your Plaid API provides a robust foundation for building any financial data application!
