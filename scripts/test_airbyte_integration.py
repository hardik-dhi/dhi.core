#!/usr/bin/env python3
"""
Test script for Plaid Airbyte Integration

This script tests the complete integration pipeline.
"""

import sys
import time
import requests
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dhi_core.plaid.client import PlaidAccount, PlaidTransaction, SessionLocal

def test_plaid_data():
    """Test if Plaid data exists."""
    print("🔍 Testing Plaid data availability...")
    
    try:
        db = SessionLocal()
        account_count = db.query(PlaidAccount).count()
        transaction_count = db.query(PlaidTransaction).count()
        db.close()
        
        print(f"✅ Found {account_count} accounts and {transaction_count} transactions")
        return account_count > 0 and transaction_count > 0
    except Exception as e:
        print(f"❌ Error checking Plaid data: {e}")
        return False

def test_plaid_api_service():
    """Test custom Plaid API service."""
    print("🔍 Testing Plaid API service...")
    
    try:
        # Health check
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("✅ Plaid API service is healthy")
        else:
            print(f"❌ Plaid API health check failed: {response.status_code}")
            return False
        
        # Test stats endpoint
        response = requests.get("http://localhost:8080/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ API Stats: {stats['accounts']} accounts, {stats['transactions']} transactions")
        else:
            print(f"❌ Stats endpoint failed: {response.status_code}")
            return False
        
        # Test accounts endpoint
        response = requests.get("http://localhost:8080/accounts?limit=5", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Accounts endpoint: {len(data.get('data', []))} records")
        else:
            print(f"❌ Accounts endpoint failed: {response.status_code}")
            return False
        
        # Test transactions endpoint
        response = requests.get("http://localhost:8080/transactions?limit=5", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Transactions endpoint: {len(data.get('data', []))} records")
        else:
            print(f"❌ Transactions endpoint failed: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error testing Plaid API service: {e}")
        return False

def test_airbyte_service():
    """Test Airbyte service."""
    print("🔍 Testing Airbyte service...")
    
    try:
        response = requests.get("http://localhost:8001/api/v1/health", timeout=10)
        if response.status_code == 200:
            print("✅ Airbyte service is healthy")
            return True
        else:
            print(f"❌ Airbyte health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing Airbyte service: {e}")
        return False

def test_database_schema():
    """Test database schema after sync."""
    print("🔍 Testing database schema...")
    
    try:
        from sqlalchemy import create_engine, text
        from dhi_core.plaid.client import get_database_url, PlaidSettings
        
        settings = PlaidSettings()
        engine = create_engine(get_database_url(settings))
        
        with engine.connect() as conn:
            # Check if airbyte_plaid schema exists
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'airbyte_plaid'
            """))
            
            if result.fetchone():
                print("✅ airbyte_plaid schema exists")
                
                # Check for tables
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'airbyte_plaid'
                """))
                
                tables = [row[0] for row in result.fetchall()]
                print(f"✅ Found tables: {', '.join(tables)}")
                
                # Count records in tables
                for table in tables:
                    if 'accounts' in table or 'transactions' in table:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM airbyte_plaid.{table}"))
                        count = result.fetchone()[0]
                        print(f"   📊 {table}: {count} records")
                
                return len(tables) > 0
            else:
                print("❌ airbyte_plaid schema not found")
                return False
                
    except Exception as e:
        print(f"❌ Error testing database schema: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 DHI Core - Plaid Airbyte Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Plaid Data", test_plaid_data),
        ("Plaid API Service", test_plaid_api_service),
        ("Airbyte Service", test_airbyte_service),
        ("Database Schema", test_database_schema)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running test: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the setup and try again.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
