#!/usr/bin/env python3
"""
Advanced Graph Query Examples

This script demonstrates advanced Cypher queries for transaction analysis
using the Neo4j graph database.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dhi_core.graph.transaction_graph import TransactionGraphDB

class AdvancedGraphQueries:
    """Collection of advanced graph queries for transaction analysis."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_username: str = "neo4j", 
                 neo4j_password: str = "dhi_password_123"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_username = neo4j_username
        self.neo4j_password = neo4j_password
    
    def find_spending_patterns(self):
        """Find recurring spending patterns."""
        print("🔍 Finding Recurring Spending Patterns...")
        
        query = """
        // Find merchants visited multiple times with similar amounts
        MATCH (m:Merchant)<-[:AT_MERCHANT]-(t1:Transaction)
        MATCH (m)<-[:AT_MERCHANT]-(t2:Transaction)
        WHERE t1 <> t2 
        AND ABS(t1.amount - t2.amount) < 5.0
        AND duration.between(t1.date, t2.date).days > 7
        AND duration.between(t1.date, t2.date).days < 35
        WITH m, 
             collect({amount: t1.amount, date: t1.date}) + collect({amount: t2.amount, date: t2.date}) as transactions,
             count(DISTINCT t1) + count(DISTINCT t2) as transaction_count
        WHERE transaction_count >= 3
        RETURN m.name as merchant,
               transaction_count,
               [tx in transactions | tx.amount] as amounts,
               [tx in transactions | tx.date] as dates
        ORDER BY transaction_count DESC
        LIMIT 10
        """
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                results = graph.execute_custom_query(query)
                
                for result in results:
                    print(f"\n🏪 {result['merchant']}")
                    print(f"   Transactions: {result['transaction_count']}")
                    amounts = result['amounts']
                    if amounts:
                        avg_amount = sum(amounts) / len(amounts)
                        print(f"   Average Amount: ${avg_amount:.2f}")
                        print(f"   Amount Range: ${min(amounts):.2f} - ${max(amounts):.2f}")
                
                return results
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def find_transaction_clusters(self):
        """Find clusters of similar transactions."""
        print("\n🎯 Finding Transaction Clusters...")
        
        query = """
        // Find groups of transactions with similar characteristics
        MATCH (t1:Transaction)-[:IN_CATEGORY]->(c:Category)<-[:IN_CATEGORY]-(t2:Transaction)
        WHERE t1 <> t2
        AND ABS(t1.amount - t2.amount) < 10.0
        AND duration.between(t1.date, t2.date).days <= 7
        WITH c.name as category,
             collect(DISTINCT {
                 id: t1.transaction_id, 
                 amount: t1.amount, 
                 date: t1.date, 
                 name: t1.name
             }) as similar_transactions
        WHERE size(similar_transactions) >= 3
        RETURN category, similar_transactions
        ORDER BY size(similar_transactions) DESC
        LIMIT 5
        """
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                results = graph.execute_custom_query(query)
                
                for result in results:
                    print(f"\n📂 Category: {result['category']}")
                    print(f"   Similar transactions: {len(result['similar_transactions'])}")
                    
                    for txn in result['similar_transactions'][:5]:
                        print(f"   • ${txn['amount']:6.2f} - {txn['name'][:40]} ({txn['date']})")
                
                return results
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def analyze_merchant_networks(self):
        """Analyze networks of merchants visited together."""
        print("\n🕸️  Analyzing Merchant Networks...")
        
        query = """
        // Find merchants that are often visited around the same time
        MATCH (a:Account)-[:HAS_TRANSACTION]->(t1:Transaction)-[:AT_MERCHANT]->(m1:Merchant)
        MATCH (a)-[:HAS_TRANSACTION]->(t2:Transaction)-[:AT_MERCHANT]->(m2:Merchant)
        WHERE m1 <> m2
        AND ABS(duration.between(t1.date, t2.date).days) <= 1
        WITH m1, m2, count(*) as co_occurrence_count
        WHERE co_occurrence_count >= 2
        RETURN m1.name as merchant1, 
               m2.name as merchant2, 
               co_occurrence_count
        ORDER BY co_occurrence_count DESC
        LIMIT 15
        """
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                results = graph.execute_custom_query(query)
                
                print("Merchants frequently visited together:")
                for result in results:
                    print(f"   🔗 {result['merchant1']} ↔ {result['merchant2']} ({result['co_occurrence_count']} times)")
                
                return results
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def detect_unusual_sequences(self):
        """Detect unusual transaction sequences."""
        print("\n⚡ Detecting Unusual Transaction Sequences...")
        
        query = """
        // Find sequences of transactions that break normal patterns
        MATCH (a:Account)-[:HAS_TRANSACTION]->(t1:Transaction)
        MATCH (a)-[:HAS_TRANSACTION]->(t2:Transaction)
        WHERE t1.date < t2.date
        AND duration.between(t1.date, t2.date).hours <= 4
        AND t1.amount > 100 AND t2.amount > 100
        AND t1.category <> t2.category
        WITH a, t1, t2,
             CASE 
                WHEN t1.amount > 500 OR t2.amount > 500 THEN 'high_amount'
                WHEN duration.between(t1.date, t2.date).minutes <= 30 THEN 'rapid_sequence'
                ELSE 'unusual_pattern'
             END as pattern_type
        RETURN a.account_id as account,
               pattern_type,
               t1.amount as first_amount,
               t1.name as first_transaction,
               t1.category as first_category,
               t2.amount as second_amount,
               t2.name as second_transaction,
               t2.category as second_category,
               duration.between(t1.date, t2.date).minutes as minutes_apart
        ORDER BY first_amount + second_amount DESC
        LIMIT 10
        """
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                results = graph.execute_custom_query(query)
                
                for result in results:
                    print(f"\n⚠️  {result['pattern_type'].replace('_', ' ').title()}")
                    print(f"   Account: {result['account']}")
                    print(f"   Sequence: ${result['first_amount']:.2f} ({result['first_category']}) → "
                          f"${result['second_amount']:.2f} ({result['second_category']})")
                    print(f"   Time Gap: {result['minutes_apart']} minutes")
                    print(f"   Transactions: {result['first_transaction'][:30]} → {result['second_transaction'][:30]}")
                
                return results
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def analyze_spending_velocity(self):
        """Analyze spending velocity and frequency."""
        print("\n🏃 Analyzing Spending Velocity...")
        
        query = """
        // Calculate spending velocity (amount per day) for different periods
        MATCH (a:Account)-[:HAS_TRANSACTION]->(t:Transaction)
        WITH a, 
             date.truncate('week', t.date) as week,
             count(t) as weekly_transactions,
             sum(t.amount) as weekly_amount
        WITH a,
             avg(weekly_transactions) as avg_weekly_transactions,
             avg(weekly_amount) as avg_weekly_amount,
             stdev(weekly_amount) as stdev_weekly_amount,
             collect({week: week, amount: weekly_amount, count: weekly_transactions}) as weekly_data
        RETURN a.name as account_name,
               a.account_id as account_id,
               avg_weekly_transactions,
               avg_weekly_amount,
               stdev_weekly_amount,
               weekly_data
        ORDER BY avg_weekly_amount DESC
        """
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                results = graph.execute_custom_query(query)
                
                for result in results:
                    print(f"\n💳 {result['account_name']} ({result['account_id']})")
                    print(f"   Avg Weekly Transactions: {result['avg_weekly_transactions']:.1f}")
                    print(f"   Avg Weekly Spending: ${result['avg_weekly_amount']:.2f}")
                    if result['stdev_weekly_amount']:
                        volatility = result['stdev_weekly_amount'] / result['avg_weekly_amount']
                        print(f"   Spending Volatility: {volatility:.2f} (StdDev/Mean)")
                
                return results
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def find_category_transitions(self):
        """Find common category transition patterns."""
        print("\n🔄 Finding Category Transition Patterns...")
        
        query = """
        // Find which categories are commonly followed by other categories
        MATCH (a:Account)-[:HAS_TRANSACTION]->(t1:Transaction)-[:IN_CATEGORY]->(c1:Category)
        MATCH (a)-[:HAS_TRANSACTION]->(t2:Transaction)-[:IN_CATEGORY]->(c2:Category)
        WHERE t1.date < t2.date
        AND duration.between(t1.date, t2.date).days <= 7
        AND c1 <> c2
        WITH c1.name as from_category, 
             c2.name as to_category, 
             count(*) as transition_count,
             avg(duration.between(t1.date, t2.date).days) as avg_days_between
        WHERE transition_count >= 2
        RETURN from_category, to_category, transition_count, avg_days_between
        ORDER BY transition_count DESC
        LIMIT 15
        """
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                results = graph.execute_custom_query(query)
                
                print("Common category transition patterns:")
                for result in results:
                    print(f"   {result['from_category']} → {result['to_category']} "
                          f"({result['transition_count']} times, avg {result['avg_days_between']:.1f} days apart)")
                
                return results
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def analyze_amount_correlations(self):
        """Analyze correlations between transaction amounts and other factors."""
        print("\n📈 Analyzing Amount Correlations...")
        
        query = """
        // Analyze amount patterns by day of week and category
        MATCH (t:Transaction)-[:IN_CATEGORY]->(c:Category)
        WITH c.name as category,
             CASE date.dayOfWeek(t.date)
               WHEN 1 THEN 'Monday'
               WHEN 2 THEN 'Tuesday'
               WHEN 3 THEN 'Wednesday'
               WHEN 4 THEN 'Thursday'
               WHEN 5 THEN 'Friday'
               WHEN 6 THEN 'Saturday'
               WHEN 7 THEN 'Sunday'
             END as day_of_week,
             avg(t.amount) as avg_amount,
             count(t) as transaction_count
        WHERE transaction_count >= 2
        RETURN category, day_of_week, avg_amount, transaction_count
        ORDER BY category, 
          CASE day_of_week
            WHEN 'Monday' THEN 1
            WHEN 'Tuesday' THEN 2
            WHEN 'Wednesday' THEN 3
            WHEN 'Thursday' THEN 4
            WHEN 'Friday' THEN 5
            WHEN 'Saturday' THEN 6
            WHEN 'Sunday' THEN 7
          END
        """
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                results = graph.execute_custom_query(query)
                
                current_category = None
                for result in results:
                    if result['category'] != current_category:
                        current_category = result['category']
                        print(f"\n📂 {current_category}:")
                    
                    print(f"   {result['day_of_week']:10s}: ${result['avg_amount']:6.2f} avg ({result['transaction_count']} txns)")
                
                return results
        except Exception as e:
            print(f"❌ Error: {e}")
            return []

def main():
    """Run all advanced graph queries."""
    print("🚀 ADVANCED GRAPH ANALYTICS")
    print("=" * 50)
    
    queries = AdvancedGraphQueries()
    
    try:
        # Run all analyses
        queries.find_spending_patterns()
        queries.find_transaction_clusters()
        queries.analyze_merchant_networks()
        queries.detect_unusual_sequences()
        queries.analyze_spending_velocity()
        queries.find_category_transitions()
        queries.analyze_amount_correlations()
        
        print("\n✅ Advanced analytics completed!")
        
    except Exception as e:
        print(f"❌ Error running advanced queries: {e}")
        print("💡 Make sure Neo4j is running and data is loaded")

if __name__ == "__main__":
    main()
