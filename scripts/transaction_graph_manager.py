#!/usr/bin/env python3
"""
Transaction Graph Manager

This script manages the transaction graph database, providing setup, data loading,
and analysis capabilities.
"""

import os
import sys
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dhi_core.graph.transaction_graph import TransactionGraphDB, AccountNode, TransactionNode

class TransactionGraphManager:
    """Manager for transaction graph database operations."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_username: str = "neo4j", 
                 neo4j_password: str = "password",
                 plaid_api_url: str = "http://localhost:8080"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_username = neo4j_username
        self.neo4j_password = neo4j_password
        self.plaid_api_url = plaid_api_url
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def setup_database(self):
        """Initialize the graph database with indexes and constraints."""
        print("🔧 Setting up graph database...")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                graph.create_indexes()
                print("✅ Database setup completed")
                return True
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            return False
    
    def check_connection(self):
        """Test connection to Neo4j database."""
        print("🔍 Testing Neo4j connection...")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                stats = graph.get_database_stats()
                print("✅ Neo4j connection successful")
                print(f"   📊 Database contains:")
                for entity, count in stats.items():
                    print(f"      • {entity}: {count}")
                return True
        except Exception as e:
            print(f"❌ Neo4j connection failed: {e}")
            print("💡 Make sure Neo4j is running and credentials are correct")
            return False
    
    def load_data(self):
        """Load transaction data from Plaid API into graph database."""
        print("📥 Loading data from Plaid API...")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                success = graph.load_data_from_plaid_api(self.plaid_api_url)
                
                if success:
                    stats = graph.get_database_stats()
                    print("✅ Data loading completed")
                    print(f"   📊 Loaded:")
                    print(f"      • {stats['transactions']} transactions")
                    print(f"      • {stats['accounts']} accounts")
                    print(f"      • {stats['merchants']} merchants")
                    print(f"      • {stats['categories']} categories")
                    print(f"      • {stats['relationships']} relationships")
                else:
                    print("❌ Data loading failed")
                
                return success
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def analyze_spending(self, days: int = 30):
        """Analyze spending patterns."""
        print(f"📊 Analyzing spending patterns (last {days} days)...")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                # Category analysis
                categories = graph.get_spending_by_category(days)
                
                print(f"\n💰 Top Spending Categories:")
                for i, cat in enumerate(categories[:10], 1):
                    print(f"   {i:2d}. {cat['category']:20s} - ${cat['total_amount']:8.2f} ({cat['transaction_count']} txns)")
                
                # Merchant analysis
                merchants = graph.get_merchant_analysis(10)
                
                print(f"\n🏪 Top Merchants:")
                for i, merchant in enumerate(merchants[:10], 1):
                    print(f"   {i:2d}. {merchant['merchant']:25s} - ${merchant['total_amount']:8.2f} ({merchant['transaction_count']} txns)")
                
                # Monthly trends
                trends = graph.get_spending_trends()
                
                print(f"\n📈 Monthly Spending Trends:")
                for trend in trends[:6]:  # Last 6 months
                    month_str = str(trend['month'])[:7]  # YYYY-MM format
                    print(f"   {month_str}: ${trend['total_amount']:8.2f} ({trend['transaction_count']} txns)")
                
                return True
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            return False
    
    def detect_anomalies(self, threshold: float = 2.0):
        """Detect anomalous transactions."""
        print(f"🔍 Detecting transaction anomalies (threshold: {threshold}x standard deviation)...")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                anomalies = graph.detect_anomalies(threshold)
                
                if anomalies:
                    print(f"\n⚠️  Found {len(anomalies)} potential anomalies:")
                    for i, anomaly in enumerate(anomalies[:10], 1):
                        print(f"   {i:2d}. ${anomaly['amount']:8.2f} - {anomaly['name'][:30]} "
                              f"(Score: {anomaly['anomaly_score']:.1f}x)")
                else:
                    print("✅ No significant anomalies detected")
                
                return True
        except Exception as e:
            print(f"❌ Anomaly detection failed: {e}")
            return False
    
    def find_similar(self, transaction_id: str):
        """Find transactions similar to the given transaction ID."""
        print(f"🔍 Finding transactions similar to {transaction_id}...")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                similar = graph.find_similar_transactions(transaction_id)
                
                if similar:
                    print(f"\n🔗 Found {len(similar)} similar transactions:")
                    for i, txn in enumerate(similar, 1):
                        print(f"   {i}. ${txn['amount']:8.2f} - {txn['name'][:30]} "
                              f"(Similarity: {txn['similarity_score']:.2f})")
                else:
                    print("❌ No similar transactions found")
                
                return True
        except Exception as e:
            print(f"❌ Similarity search failed: {e}")
            return False
    
    def account_summary(self, account_id: str):
        """Get detailed summary for an account."""
        print(f"📋 Account summary for {account_id}...")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                summary = graph.get_account_summary(account_id)
                
                if summary:
                    print(f"\n💳 Account Details:")
                    print(f"   Name: {summary['account_name']}")
                    print(f"   Type: {summary['account_type']}")
                    print(f"   Institution: {summary['institution']}")
                    print(f"   Transactions: {summary['transaction_count']}")
                    print(f"   Total Amount: ${summary['total_amount']:.2f}")
                    print(f"   Average: ${summary['avg_amount']:.2f}")
                    print(f"   Date Range: {summary['earliest_transaction']} to {summary['latest_transaction']}")
                    print(f"   Categories: {', '.join(summary['categories'])}")
                else:
                    print("❌ Account not found")
                
                return True
        except Exception as e:
            print(f"❌ Account summary failed: {e}")
            return False
    
    def custom_query(self, query: str, params: str = "{}"):
        """Execute a custom Cypher query."""
        print("🔧 Executing custom query...")
        
        try:
            parameters = json.loads(params) if params != "{}" else {}
            
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                results = graph.execute_custom_query(query, parameters)
                
                print(f"✅ Query executed successfully. Results ({len(results)} rows):")
                
                if results:
                    # Print headers
                    headers = list(results[0].keys())
                    print("   " + " | ".join(f"{h:15s}" for h in headers))
                    print("   " + "-" * (len(headers) * 18))
                    
                    # Print rows (limit to 20)
                    for row in results[:20]:
                        values = [str(row[h])[:15] for h in headers]
                        print("   " + " | ".join(f"{v:15s}" for v in values))
                    
                    if len(results) > 20:
                        print(f"   ... and {len(results) - 20} more rows")
                
                return True
        except json.JSONDecodeError:
            print("❌ Invalid JSON parameters")
            return False
        except Exception as e:
            print(f"❌ Query execution failed: {e}")
            return False
    
    def export_data(self, format: str = "json", output_path: str = "/tmp"):
        """Export graph data to various formats."""
        print(f"📤 Exporting data in {format} format...")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                
                if format.lower() == "json":
                    # Export key analytics as JSON
                    data = {
                        'stats': graph.get_database_stats(),
                        'spending_by_category': graph.get_spending_by_category(30),
                        'top_merchants': graph.get_merchant_analysis(20),
                        'monthly_trends': graph.get_spending_trends(),
                        'anomalies': graph.detect_anomalies()
                    }
                    
                    output_file = f"{output_path}/transaction_graph_export.json"
                    with open(output_file, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
                    
                    print(f"✅ Data exported to {output_file}")
                
                elif format.lower() == "cypher":
                    # Export as Cypher statements
                    output_file = f"{output_path}/transaction_graph_export.cypher"
                    
                    # This would require custom export logic
                    print("⚠️  Cypher export not yet implemented")
                
                return True
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False
    
    def clear_database(self):
        """Clear all data from the graph database."""
        print("⚠️  WARNING: This will delete ALL data from the graph database!")
        confirm = input("Type 'DELETE ALL' to confirm: ")
        
        if confirm == "DELETE ALL":
            try:
                with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                    graph.clear_database()
                    print("✅ Database cleared")
                    return True
            except Exception as e:
                print(f"❌ Failed to clear database: {e}")
                return False
        else:
            print("❌ Operation cancelled")
            return False

def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Transaction Graph Database Manager")
    
    # Connection parameters
    parser.add_argument('--neo4j-uri', default='bolt://localhost:7687',
                       help='Neo4j database URI')
    parser.add_argument('--neo4j-username', default='neo4j',
                       help='Neo4j username')
    parser.add_argument('--neo4j-password', default='password',
                       help='Neo4j password')
    parser.add_argument('--plaid-api', default='http://localhost:8080',
                       help='Plaid API URL')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup database
    subparsers.add_parser('setup', help='Initialize graph database with indexes')
    
    # Check connection
    subparsers.add_parser('check', help='Test Neo4j connection')
    
    # Load data
    subparsers.add_parser('load', help='Load data from Plaid API')
    
    # Analysis commands
    analyze_parser = subparsers.add_parser('analyze', help='Analyze spending patterns')
    analyze_parser.add_argument('--days', type=int, default=30,
                               help='Number of days to analyze')
    
    # Anomaly detection
    anomaly_parser = subparsers.add_parser('anomalies', help='Detect transaction anomalies')
    anomaly_parser.add_argument('--threshold', type=float, default=2.0,
                               help='Anomaly detection threshold')
    
    # Similar transactions
    similar_parser = subparsers.add_parser('similar', help='Find similar transactions')
    similar_parser.add_argument('transaction_id', help='Transaction ID to find similar to')
    
    # Account summary
    account_parser = subparsers.add_parser('account', help='Get account summary')
    account_parser.add_argument('account_id', help='Account ID to analyze')
    
    # Custom query
    query_parser = subparsers.add_parser('query', help='Execute custom Cypher query')
    query_parser.add_argument('cypher', help='Cypher query to execute')
    query_parser.add_argument('--params', default='{}', help='Query parameters as JSON')
    
    # Export data
    export_parser = subparsers.add_parser('export', help='Export graph data')
    export_parser.add_argument('--format', choices=['json', 'cypher'], default='json',
                              help='Export format')
    export_parser.add_argument('--output', default='/tmp', help='Output directory')
    
    # Clear database
    subparsers.add_parser('clear', help='Clear all data from database')
    
    # Full initialization
    subparsers.add_parser('init', help='Complete setup: setup + load + analyze')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = TransactionGraphManager(
        neo4j_uri=args.neo4j_uri,
        neo4j_username=args.neo4j_username,
        neo4j_password=args.neo4j_password,
        plaid_api_url=args.plaid_api
    )
    
    print("🌐 Transaction Graph Database Manager")
    print("=" * 50)
    
    try:
        if args.command == 'setup':
            manager.setup_database()
        
        elif args.command == 'check':
            manager.check_connection()
        
        elif args.command == 'load':
            manager.load_data()
        
        elif args.command == 'analyze':
            manager.analyze_spending(args.days)
        
        elif args.command == 'anomalies':
            manager.detect_anomalies(args.threshold)
        
        elif args.command == 'similar':
            manager.find_similar(args.transaction_id)
        
        elif args.command == 'account':
            manager.account_summary(args.account_id)
        
        elif args.command == 'query':
            manager.custom_query(args.cypher, args.params)
        
        elif args.command == 'export':
            manager.export_data(args.format, args.output)
        
        elif args.command == 'clear':
            manager.clear_database()
        
        elif args.command == 'init':
            if manager.setup_database():
                if manager.load_data():
                    manager.analyze_spending()
        
        else:
            print(f"❌ Unknown command: {args.command}")
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
