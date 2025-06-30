#!/usr/bin/env python3
"""
Graph Database Test Script

This script tests the graph database functionality without requiring Neo4j to be running.
It demonstrates the data structures and query patterns that would be used.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import json

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dhi_core.graph.transaction_graph import (
    TransactionNode, AccountNode, MerchantNode, CategoryNode
)

class MockGraphDatabase:
    """Mock graph database for testing without Neo4j."""
    
    def __init__(self):
        self.transactions = []
        self.accounts = []
        self.merchants = []
        self.categories = []
    
    def add_sample_data(self):
        """Add sample transaction data for demonstration."""
        
        # Sample accounts
        accounts = [
            AccountNode(
                account_id="acc_001",
                name="Chase Checking",
                type="depository",
                subtype="checking",
                institution_name="Chase Bank",
                mask="0123"
            ),
            AccountNode(
                account_id="acc_002", 
                name="Savings Account",
                type="depository",
                subtype="savings",
                institution_name="Chase Bank",
                mask="0456"
            )
        ]
        
        # Sample transactions
        transactions = [
            TransactionNode(
                transaction_id="txn_001",
                amount=45.67,
                date="2025-06-20",
                name="Starbucks Coffee",
                category="Food and Drink",
                subcategory="Coffee Shops",
                merchant_name="Starbucks",
                account_id="acc_001"
            ),
            TransactionNode(
                transaction_id="txn_002", 
                amount=125.00,
                date="2025-06-21",
                name="Grocery Store",
                category="Food and Drink",
                subcategory="Groceries",
                merchant_name="Whole Foods",
                account_id="acc_001"
            ),
            TransactionNode(
                transaction_id="txn_003",
                amount=800.00,
                date="2025-06-22", 
                name="Rent Payment",
                category="Payment",
                subcategory="Rent",
                merchant_name="Property Management",
                account_id="acc_001"
            ),
            TransactionNode(
                transaction_id="txn_004",
                amount=25.99,
                date="2025-06-23",
                name="Netflix Subscription",
                category="Entertainment", 
                subcategory="Digital Services",
                merchant_name="Netflix",
                account_id="acc_001"
            ),
            TransactionNode(
                transaction_id="txn_005",
                amount=89.50,
                date="2025-06-24",
                name="Gas Station",
                category="Transportation", 
                subcategory="Gas Stations",
                merchant_name="Shell",
                account_id="acc_002"
            )
        ]
        
        self.accounts = accounts
        self.transactions = transactions
        
        # Extract unique merchants and categories
        merchants = set()
        categories = set()
        
        for txn in transactions:
            if txn.merchant_name:
                merchants.add(txn.merchant_name)
            if txn.category:
                categories.add(txn.category)
        
        self.merchants = [MerchantNode(name=m) for m in merchants]
        self.categories = [CategoryNode(name=c) for c in categories]
    
    def analyze_spending_by_category(self) -> List[Dict[str, Any]]:
        """Analyze spending by category."""
        category_totals = {}
        
        for txn in self.transactions:
            category = txn.category
            if category not in category_totals:
                category_totals[category] = {
                    'category': category,
                    'total_amount': 0,
                    'transaction_count': 0,
                    'transactions': []
                }
            
            category_totals[category]['total_amount'] += txn.amount
            category_totals[category]['transaction_count'] += 1
            category_totals[category]['transactions'].append(txn)
        
        # Sort by total amount
        return sorted(category_totals.values(), key=lambda x: x['total_amount'], reverse=True)
    
    def analyze_merchants(self) -> List[Dict[str, Any]]:
        """Analyze merchant spending."""
        merchant_totals = {}
        
        for txn in self.transactions:
            merchant = txn.merchant_name
            if not merchant:
                continue
                
            if merchant not in merchant_totals:
                merchant_totals[merchant] = {
                    'merchant': merchant,
                    'total_amount': 0,
                    'transaction_count': 0,
                    'avg_amount': 0,
                    'transactions': []
                }
            
            merchant_totals[merchant]['total_amount'] += txn.amount
            merchant_totals[merchant]['transaction_count'] += 1
            merchant_totals[merchant]['transactions'].append(txn)
        
        # Calculate averages
        for merchant_data in merchant_totals.values():
            merchant_data['avg_amount'] = merchant_data['total_amount'] / merchant_data['transaction_count']
        
        return sorted(merchant_totals.values(), key=lambda x: x['total_amount'], reverse=True)
    
    def detect_anomalies(self, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """Detect transaction anomalies."""
        if len(self.transactions) < 3:
            return []
        
        amounts = [txn.amount for txn in self.transactions]
        avg_amount = sum(amounts) / len(amounts)
        
        # Simple standard deviation calculation
        variance = sum((x - avg_amount) ** 2 for x in amounts) / len(amounts)
        std_dev = variance ** 0.5
        
        anomalies = []
        for txn in self.transactions:
            deviation = abs(txn.amount - avg_amount)
            if deviation > (threshold * std_dev):
                anomaly_score = deviation / std_dev
                anomalies.append({
                    'transaction_id': txn.transaction_id,
                    'name': txn.name,
                    'amount': txn.amount,
                    'date': txn.date,
                    'category': txn.category,
                    'anomaly_score': anomaly_score,
                    'avg_amount': avg_amount
                })
        
        return sorted(anomalies, key=lambda x: x['anomaly_score'], reverse=True)
    
    def find_similar_transactions(self, target_txn_id: str) -> List[Dict[str, Any]]:
        """Find similar transactions."""
        target_txn = None
        for txn in self.transactions:
            if txn.transaction_id == target_txn_id:
                target_txn = txn
                break
        
        if not target_txn:
            return []
        
        similar = []
        for txn in self.transactions:
            if txn.transaction_id == target_txn_id:
                continue
            
            similarity_score = 0.0
            
            # Same merchant
            if txn.merchant_name == target_txn.merchant_name:
                similarity_score += 1.0
            
            # Same category
            if txn.category == target_txn.category:
                similarity_score += 0.5
            
            # Similar amount (within 20%)
            if target_txn.amount > 0:
                amount_diff = abs(txn.amount - target_txn.amount) / target_txn.amount
                if amount_diff < 0.2:
                    similarity_score += 0.3
            
            if similarity_score > 0.5:
                similar.append({
                    'transaction_id': txn.transaction_id,
                    'name': txn.name,
                    'amount': txn.amount,
                    'date': txn.date,
                    'category': txn.category,
                    'merchant': txn.merchant_name,
                    'similarity_score': similarity_score
                })
        
        return sorted(similar, key=lambda x: x['similarity_score'], reverse=True)
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        return {
            'transactions': len(self.transactions),
            'accounts': len(self.accounts),
            'merchants': len(self.merchants),
            'categories': len(self.categories),
            'relationships': len(self.transactions) * 3  # Each transaction has 3 relationships
        }

def demonstrate_graph_analytics():
    """Demonstrate graph database analytics capabilities."""
    print("🚀 GRAPH DATABASE ANALYTICS DEMONSTRATION")
    print("=" * 60)
    
    # Initialize mock database with sample data
    db = MockGraphDatabase()
    db.add_sample_data()
    
    # Database overview
    print("\n📊 Database Overview")
    print("-" * 30)
    stats = db.get_database_stats()
    for entity, count in stats.items():
        print(f"   {entity.capitalize()}: {count}")
    
    # Spending by category analysis
    print("\n💰 Spending by Category")
    print("-" * 30)
    categories = db.analyze_spending_by_category()
    for i, cat in enumerate(categories, 1):
        percentage = (cat['total_amount'] / sum(c['total_amount'] for c in categories)) * 100
        print(f"   {i}. {cat['category']:20s} ${cat['total_amount']:8.2f} ({percentage:5.1f}%) - {cat['transaction_count']} txns")
    
    # Merchant analysis
    print("\n🏪 Top Merchants")
    print("-" * 30)
    merchants = db.analyze_merchants()
    for i, merchant in enumerate(merchants, 1):
        print(f"   {i}. {merchant['merchant']:20s} ${merchant['total_amount']:8.2f} (Avg: ${merchant['avg_amount']:6.2f})")
    
    # Anomaly detection
    print("\n⚠️  Anomaly Detection")
    print("-" * 30)
    anomalies = db.detect_anomalies(1.5)  # Lower threshold for demo
    if anomalies:
        for anomaly in anomalies:
            print(f"   🚨 ${anomaly['amount']:8.2f} - {anomaly['name']} (Score: {anomaly['anomaly_score']:.1f}x)")
    else:
        print("   ✅ No significant anomalies detected")
    
    # Similar transactions
    print("\n🔍 Similar Transaction Analysis")
    print("-" * 30)
    if db.transactions:
        target_txn = db.transactions[0]  # Use first transaction as example
        print(f"   Target: {target_txn.name} (${target_txn.amount})")
        
        similar = db.find_similar_transactions(target_txn.transaction_id)
        if similar:
            for sim in similar[:3]:  # Top 3 similar
                print(f"   • {sim['name']:30s} ${sim['amount']:8.2f} (Similarity: {sim['similarity_score']:.2f})")
        else:
            print("   No similar transactions found")
    
    # Account summary
    print("\n💳 Account Summary")
    print("-" * 30)
    account_totals = {}
    for txn in db.transactions:
        acc_id = txn.account_id
        if acc_id not in account_totals:
            # Find account details
            account = next((acc for acc in db.accounts if acc.account_id == acc_id), None)
            account_totals[acc_id] = {
                'name': account.name if account else acc_id,
                'total': 0,
                'count': 0
            }
        account_totals[acc_id]['total'] += txn.amount
        account_totals[acc_id]['count'] += 1
    
    for acc_id, data in account_totals.items():
        avg_amount = data['total'] / data['count']
        print(f"   {data['name']:20s} ${data['total']:8.2f} ({data['count']} txns, avg: ${avg_amount:.2f})")
    
    print("\n✅ Graph analytics demonstration completed!")
    print("\n💡 Next Steps:")
    print("   1. Start Docker: sudo systemctl start docker")
    print("   2. Setup Neo4j: ./scripts/setup_neo4j.sh setup")
    print("   3. Run full analytics: ./scripts/analytics_dashboard.py")
    
    return True

def export_sample_data():
    """Export sample data for testing."""
    db = MockGraphDatabase()
    db.add_sample_data()
    
    sample_data = {
        'accounts': [
            {
                'account_id': acc.account_id,
                'name': acc.name,
                'type': acc.type,
                'subtype': acc.subtype,
                'institution_name': acc.institution_name,
                'mask': acc.mask
            } for acc in db.accounts
        ],
        'transactions': [
            {
                'transaction_id': txn.transaction_id,
                'amount': txn.amount,
                'date': txn.date,
                'name': txn.name,
                'category': txn.category,
                'subcategory': txn.subcategory,
                'merchant_name': txn.merchant_name,
                'account_id': txn.account_id
            } for txn in db.transactions
        ]
    }
    
    output_file = "/tmp/sample_transaction_data.json"
    with open(output_file, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"📤 Sample data exported to: {output_file}")
    print(f"   Contains {len(sample_data['accounts'])} accounts and {len(sample_data['transactions'])} transactions")
    
    return output_file

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        export_sample_data()
    else:
        demonstrate_graph_analytics()
