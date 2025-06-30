#!/usr/bin/env python3
"""
Plaid Airbyte Integration Manager

This script manages the complete integration between Plaid and Airbyte for syncing
transaction data to PostgreSQL.
"""

import os
import sys
import argparse
import subprocess
import time
import requests
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dhi_core.plaid.client import PlaidAccount, PlaidTransaction, SessionLocal

class PlaidAirbyteManager:
    def __init__(self):
        self.project_root = project_root
        self.airbyte_dir = self.project_root / "airbyte"
        self.airbyte_url = "http://localhost:8001"
        self.plaid_api_url = "http://localhost:8080"
    
    def check_dependencies(self):
        """Check if required dependencies are available."""
        print("🔍 Checking dependencies...")
        
        # Check Docker
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker: {result.stdout.strip()}")
            else:
                print("❌ Docker not found")
                return False
        except FileNotFoundError:
            print("❌ Docker not found")
            return False
        
        # Check Docker Compose
        try:
            result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker Compose: {result.stdout.strip()}")
            else:
                print("❌ Docker Compose not found")
                return False
        except FileNotFoundError:
            print("❌ Docker Compose not found")
            return False
        
        # Check if Plaid data exists
        try:
            db = SessionLocal()
            account_count = db.query(PlaidAccount).count()
            transaction_count = db.query(PlaidTransaction).count()
            db.close()
            
            print(f"✅ Found {account_count} Plaid accounts and {transaction_count} transactions")
            
            if account_count == 0:
                print("⚠️  No Plaid accounts found. You may want to link some accounts first.")
        except Exception as e:
            print(f"⚠️  Could not check Plaid data: {e}")
        
        return True
    
    def start_services(self):
        """Start Airbyte and Plaid API services."""
        print("🚀 Starting Airbyte and Plaid API services...")
        
        os.chdir(self.airbyte_dir)
        
        try:
            # Start services
            subprocess.run(["docker-compose", "up", "-d"], check=True)
            print("✅ Services started successfully!")
            
            # Wait for services to be ready
            self.wait_for_services()
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start services: {e}")
            return False
        
        return True
    
    def stop_services(self):
        """Stop Airbyte and Plaid API services."""
        print("🛑 Stopping services...")
        
        os.chdir(self.airbyte_dir)
        
        try:
            subprocess.run(["docker-compose", "down"], check=True)
            print("✅ Services stopped successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to stop services: {e}")
            return False
        
        return True
    
    def wait_for_services(self):
        """Wait for services to be ready."""
        print("⏳ Waiting for services to be ready...")
        
        # Wait for Airbyte
        for attempt in range(30):
            try:
                response = requests.get(f"{self.airbyte_url}/api/v1/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Airbyte is ready!")
                    break
            except:
                pass
            time.sleep(10)
            print(f"   Attempt {attempt + 1}/30 - Still waiting for Airbyte...")
        else:
            print("❌ Airbyte failed to start in time")
            return False
        
        # Wait for Plaid API
        for attempt in range(30):
            try:
                response = requests.get(f"{self.plaid_api_url}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Plaid API is ready!")
                    break
            except:
                pass
            time.sleep(5)
            print(f"   Attempt {attempt + 1}/30 - Still waiting for Plaid API...")
        else:
            print("❌ Plaid API failed to start in time")
            return False
        
        return True
    
    def show_status(self):
        """Show status of services and data."""
        print("📊 Service Status:")
        print("=" * 40)
        
        # Check Airbyte
        try:
            response = requests.get(f"{self.airbyte_url}/api/v1/health", timeout=5)
            if response.status_code == 200:
                print("✅ Airbyte: Running")
            else:
                print("❌ Airbyte: Not responding")
        except:
            print("❌ Airbyte: Not accessible")
        
        # Check Plaid API
        try:
            response = requests.get(f"{self.plaid_api_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Plaid API: Running")
                
                # Get stats
                stats_response = requests.get(f"{self.plaid_api_url}/stats", timeout=5)
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    print(f"   📈 {stats['accounts']} accounts, {stats['transactions']} transactions")
                    if stats['date_range']['earliest']:
                        print(f"   📅 Data range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
            else:
                print("❌ Plaid API: Not responding")
        except:
            print("❌ Plaid API: Not accessible")
        
        # Check Docker containers
        try:
            result = subprocess.run(
                ["docker-compose", "ps"], 
                cwd=self.airbyte_dir,
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                print("\n🐳 Docker Containers:")
                print(result.stdout)
        except:
            pass
    
    def sync_plaid_data(self):
        """Trigger a sync of Plaid data."""
        print("🔄 Triggering Plaid data sync...")
        
        try:
            response = requests.post(f"{self.plaid_api_url}/sync/full", timeout=30)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Sync completed!")
                print(f"   📊 Synced {result['synced_accounts']} accounts")
                print(f"   💳 Added {result['total_transactions']} transactions")
            else:
                print(f"❌ Sync failed: {response.text}")
        except Exception as e:
            print(f"❌ Error during sync: {e}")
    
    def show_logs(self, service=None):
        """Show logs for services."""
        os.chdir(self.airbyte_dir)
        
        if service:
            print(f"📋 Showing logs for {service}...")
            subprocess.run(["docker-compose", "logs", "-f", service])
        else:
            print("📋 Showing all service logs...")
            subprocess.run(["docker-compose", "logs", "-f"])
    
    def setup_airbyte(self):
        """Set up Airbyte connections and sources."""
        print("⚙️  Setting up Airbyte configuration...")
        
        # Import and run setup script
        try:
            from scripts.airbyte_setup import AirbyteSetup
            setup = AirbyteSetup(self.airbyte_url)
            return setup.setup_complete_pipeline()
        except Exception as e:
            print(f"❌ Error setting up Airbyte: {e}")
            return False
    
    def consume_data(self, output_format="json", output_path="/tmp"):
        """Consume and export Plaid data in various formats."""
        print("📥 Consuming Plaid data...")
        
        try:
            # Get data from API
            accounts_response = requests.get(f"{self.plaid_api_url}/accounts", timeout=10)
            transactions_response = requests.get(f"{self.plaid_api_url}/transactions", timeout=10)
            
            if accounts_response.status_code == 200 and transactions_response.status_code == 200:
                accounts = accounts_response.json()["data"]
                transactions = transactions_response.json()["data"]
                
                print(f"✅ Retrieved {len(accounts)} accounts and {len(transactions)} transactions")
                
                if output_format.lower() == "json":
                    # Export as JSON
                    import json
                    from datetime import datetime
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    accounts_file = f"{output_path}/plaid_accounts_{timestamp}.json"
                    transactions_file = f"{output_path}/plaid_transactions_{timestamp}.json"
                    
                    with open(accounts_file, 'w') as f:
                        json.dump(accounts, f, indent=2, default=str)
                    
                    with open(transactions_file, 'w') as f:
                        json.dump(transactions, f, indent=2, default=str)
                    
                    print(f"📄 Accounts saved to: {accounts_file}")
                    print(f"📄 Transactions saved to: {transactions_file}")
                
                elif output_format.lower() == "csv":
                    # Export as CSV
                    import pandas as pd
                    from datetime import datetime
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Create DataFrames
                    accounts_df = pd.DataFrame(accounts)
                    transactions_df = pd.DataFrame(transactions)
                    
                    # Add account names to transactions
                    account_lookup = {acc['account_id']: acc['name'] for acc in accounts}
                    transactions_df['account_name'] = transactions_df['account_id'].map(account_lookup)
                    
                    # Export files
                    accounts_file = f"{output_path}/plaid_accounts_{timestamp}.csv"
                    transactions_file = f"{output_path}/plaid_transactions_{timestamp}.csv"
                    
                    accounts_df.to_csv(accounts_file, index=False)
                    transactions_df.to_csv(transactions_file, index=False)
                    
                    print(f"📊 Accounts saved to: {accounts_file}")
                    print(f"📊 Transactions saved to: {transactions_file}")
                
                elif output_format.lower() == "summary":
                    # Print summary to console
                    print("\n📊 DATA SUMMARY")
                    print("=" * 40)
                    
                    print(f"💳 Accounts ({len(accounts)}):")
                    for i, acc in enumerate(accounts, 1):
                        print(f"   {i}. {acc['name']} ({acc['type']}) - {acc['institution_name']}")
                    
                    print(f"\n💰 Transactions ({len(transactions)}):")
                    total_amount = sum(float(t['amount']) for t in transactions)
                    print(f"   Total amount: ${total_amount:.2f}")
                    
                    # Category breakdown
                    from collections import defaultdict
                    categories = defaultdict(float)
                    for t in transactions:
                        categories[t.get('category', 'Other')] += float(t['amount'])
                    
                    print(f"   Top categories:")
                    for cat, amount in sorted(categories.items(), key=lambda x: abs(x[1]), reverse=True)[:5]:
                        print(f"     • {cat}: ${amount:.2f}")
                    
                    # Recent transactions
                    recent = sorted(transactions, key=lambda x: x['date'], reverse=True)[:5]
                    print(f"   Recent transactions:")
                    for t in recent:
                        print(f"     • ${float(t['amount']):6.2f} - {t['name']} ({t['date']})")
                
                return True
            else:
                print(f"❌ Failed to retrieve data. Status codes: {accounts_response.status_code}, {transactions_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error consuming data: {e}")
            return False

def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Plaid Airbyte Integration Manager")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Check dependencies
    subparsers.add_parser('check', help='Check dependencies and system status')
    
    # Start services
    subparsers.add_parser('start', help='Start Airbyte and Plaid API services')
    
    # Stop services
    subparsers.add_parser('stop', help='Stop all services')
    
    # Show status
    subparsers.add_parser('status', help='Show service status and data stats')
    
    # Sync data
    subparsers.add_parser('sync', help='Trigger Plaid data sync')
    
    # Setup Airbyte
    subparsers.add_parser('setup', help='Set up Airbyte connections and sources')
    
    # Show logs
    logs_parser = subparsers.add_parser('logs', help='Show service logs')
    logs_parser.add_argument('--service', help='Specific service to show logs for')
    
    # Full setup
    subparsers.add_parser('init', help='Complete initialization (start + setup)')
    
    # Consume data
    consume_parser = subparsers.add_parser('consume', help='Consume and export Plaid data')
    consume_parser.add_argument('--format', help='Output format (json, csv, summary)', default='json')
    consume_parser.add_argument('--output', help='Output directory', default='/tmp')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = PlaidAirbyteManager()
    
    print("🏦 DHI Core - Plaid Airbyte Integration Manager")
    print("=" * 50)
    
    if args.command == 'check':
        manager.check_dependencies()
    
    elif args.command == 'start':
        manager.start_services()
    
    elif args.command == 'stop':
        manager.stop_services()
    
    elif args.command == 'status':
        manager.show_status()
    
    elif args.command == 'sync':
        manager.sync_plaid_data()
    
    elif args.command == 'setup':
        manager.setup_airbyte()
    
    elif args.command == 'logs':
        manager.show_logs(args.service)
    
    elif args.command == 'init':
        if manager.check_dependencies():
            if manager.start_services():
                time.sleep(10)  # Give services time to fully start
                manager.setup_airbyte()
                manager.show_status()
    
    elif args.command == 'consume':
        manager.consume_data(args.format, args.output)
    
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()

if __name__ == "__main__":
    main()
