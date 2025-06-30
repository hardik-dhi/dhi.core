#!/usr/bin/env python3
"""
Transaction Graph Analytics Dashboard

This script provides an interactive dashboard for exploring transaction relationships
and patterns using the Neo4j graph database.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dhi_core.graph.transaction_graph import TransactionGraphDB

class TransactionAnalyticsDashboard:
    """Interactive analytics dashboard for transaction graph data."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_username: str = "neo4j", 
                 neo4j_password: str = "dhi_password_123"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_username = neo4j_username
        self.neo4j_password = neo4j_password
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def print_header(self, title: str):
        """Print a formatted header."""
        print("\n" + "="*60)
        print(f"  {title}")
        print("="*60)
    
    def print_section(self, title: str):
        """Print a formatted section header."""
        print(f"\n📊 {title}")
        print("-" * (len(title) + 4))
    
    def dashboard_overview(self):
        """Show comprehensive dashboard overview."""
        self.print_header("TRANSACTION ANALYTICS DASHBOARD")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                
                # Database statistics
                self.print_section("Database Overview")
                stats = graph.get_database_stats()
                print(f"💳 Accounts:       {stats['accounts']:,}")
                print(f"💸 Transactions:   {stats['transactions']:,}")
                print(f"🏪 Merchants:      {stats['merchants']:,}")
                print(f"📂 Categories:     {stats['categories']:,}")
                print(f"🔗 Relationships: {stats['relationships']:,}")
                
                # Spending by category (last 30 days)
                self.print_section("Top Spending Categories (Last 30 Days)")
                categories = graph.get_spending_by_category(30)
                for i, cat in enumerate(categories[:10], 1):
                    percentage = (cat['total_amount'] / sum(c['total_amount'] for c in categories)) * 100
                    print(f"{i:2d}. {cat['category']:20s} ${cat['total_amount']:8.2f} ({percentage:5.1f}%) - {cat['transaction_count']} txns")
                
                # Top merchants
                self.print_section("Top Merchants by Spending")
                merchants = graph.get_merchant_analysis(10)
                for i, merchant in enumerate(merchants[:10], 1):
                    avg_amount = merchant['avg_amount']
                    print(f"{i:2d}. {merchant['merchant']:25s} ${merchant['total_amount']:8.2f} (Avg: ${avg_amount:6.2f}) - {merchant['transaction_count']} txns")
                
                # Monthly trends
                self.print_section("Monthly Spending Trends")
                trends = graph.get_spending_trends()
                for trend in trends[:6]:  # Last 6 months
                    month_str = str(trend['month'])[:7]  # YYYY-MM format
                    print(f"{month_str}: ${trend['total_amount']:8.2f} ({trend['transaction_count']:3d} txns) - Avg: ${trend['avg_amount']:6.2f}")
                
                # Anomaly detection
                self.print_section("Recent Anomalies (2x Standard Deviation)")
                anomalies = graph.detect_anomalies(2.0)
                if anomalies:
                    for i, anomaly in enumerate(anomalies[:5], 1):
                        print(f"{i}. ${anomaly['amount']:8.2f} - {anomaly['name'][:40]} (Score: {anomaly['anomaly_score']:.1f}x)")
                else:
                    print("✅ No significant anomalies detected")
                
                return True
        
        except Exception as e:
            print(f"❌ Dashboard error: {e}")
            return False
    
    def category_deep_dive(self, category_name: str = None):
        """Deep dive analysis for a specific category."""
        if not category_name:
            # Show available categories first
            try:
                with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                    categories = graph.get_spending_by_category(90)
                    
                    self.print_header("CATEGORY ANALYSIS")
                    print("Available categories:")
                    for i, cat in enumerate(categories[:15], 1):
                        print(f"{i:2d}. {cat['category']}")
                    
                    return True
            except Exception as e:
                print(f"❌ Error loading categories: {e}")
                return False
        
        self.print_header(f"CATEGORY DEEP DIVE: {category_name.upper()}")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                
                # Category-specific query
                query = """
                MATCH (t:Transaction)-[:IN_CATEGORY]->(c:Category {name: $category})
                OPTIONAL MATCH (t)-[:AT_MERCHANT]->(m:Merchant)
                RETURN t.amount as amount,
                       t.name as transaction_name,
                       t.date as date,
                       m.name as merchant,
                       t.account_id as account
                ORDER BY t.date DESC
                LIMIT 50
                """
                
                transactions = graph.execute_custom_query(query, {'category': category_name})
                
                if not transactions:
                    print(f"No transactions found for category: {category_name}")
                    return False
                
                # Statistics
                amounts = [t['amount'] for t in transactions]
                total_amount = sum(amounts)
                avg_amount = total_amount / len(amounts)
                
                self.print_section("Category Statistics")
                print(f"Total Transactions: {len(transactions)}")
                print(f"Total Amount:      ${total_amount:,.2f}")
                print(f"Average Amount:    ${avg_amount:,.2f}")
                print(f"Max Amount:        ${max(amounts):,.2f}")
                print(f"Min Amount:        ${min(amounts):,.2f}")
                
                # Top merchants in category
                merchant_totals = {}
                for txn in transactions:
                    if txn['merchant']:
                        merchant = txn['merchant']
                        merchant_totals[merchant] = merchant_totals.get(merchant, 0) + txn['amount']
                
                if merchant_totals:
                    self.print_section("Top Merchants in Category")
                    sorted_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)
                    for i, (merchant, amount) in enumerate(sorted_merchants[:10], 1):
                        print(f"{i:2d}. {merchant[:30]:30s} ${amount:8.2f}")
                
                # Recent transactions
                self.print_section("Recent Transactions")
                for i, txn in enumerate(transactions[:10], 1):
                    date_str = str(txn['date'])[:10]
                    merchant_str = txn['merchant'][:20] if txn['merchant'] else "Unknown"
                    print(f"{i:2d}. {date_str} - ${txn['amount']:8.2f} - {merchant_str} - {txn['transaction_name'][:30]}")
                
                return True
        
        except Exception as e:
            print(f"❌ Category analysis error: {e}")
            return False
    
    def merchant_relationship_analysis(self):
        """Analyze relationships between merchants and spending patterns."""
        self.print_header("MERCHANT RELATIONSHIP ANALYSIS")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                
                # Merchants with multiple categories
                query = """
                MATCH (m:Merchant)<-[:AT_MERCHANT]-(t:Transaction)-[:IN_CATEGORY]->(c:Category)
                WITH m, collect(DISTINCT c.name) as categories, count(t) as transaction_count, sum(t.amount) as total_amount
                WHERE size(categories) > 1
                RETURN m.name as merchant, categories, transaction_count, total_amount
                ORDER BY total_amount DESC
                LIMIT 20
                """
                
                multi_category_merchants = graph.execute_custom_query(query)
                
                self.print_section("Merchants Spanning Multiple Categories")
                for i, merchant in enumerate(multi_category_merchants[:10], 1):
                    categories_str = ", ".join(merchant['categories'][:3])
                    if len(merchant['categories']) > 3:
                        categories_str += f" (+{len(merchant['categories'])-3} more)"
                    print(f"{i:2d}. {merchant['merchant']:25s} - {categories_str}")
                    print(f"     ${merchant['total_amount']:8.2f} across {merchant['transaction_count']} transactions")
                
                # Spending frequency patterns
                self.print_section("High-Frequency Merchants")
                query = """
                MATCH (m:Merchant)<-[:AT_MERCHANT]-(t:Transaction)
                WITH m, count(t) as frequency, sum(t.amount) as total, avg(t.amount) as avg_amount
                WHERE frequency >= 3
                RETURN m.name as merchant, frequency, total, avg_amount
                ORDER BY frequency DESC
                LIMIT 15
                """
                
                frequent_merchants = graph.execute_custom_query(query)
                for i, merchant in enumerate(frequent_merchants[:10], 1):
                    print(f"{i:2d}. {merchant['merchant']:25s} - {merchant['frequency']:2d} visits - ${merchant['total']:8.2f} (Avg: ${merchant['avg_amount']:6.2f})")
                
                return True
        
        except Exception as e:
            print(f"❌ Merchant analysis error: {e}")
            return False
    
    def account_comparison(self):
        """Compare spending patterns across accounts."""
        self.print_header("ACCOUNT COMPARISON ANALYSIS")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                
                # Get all accounts with transaction summaries
                query = """
                MATCH (a:Account)-[:HAS_TRANSACTION]->(t:Transaction)
                WITH a, count(t) as transaction_count, sum(t.amount) as total_amount, avg(t.amount) as avg_amount
                RETURN a.account_id as account_id, a.name as account_name, a.type as account_type,
                       transaction_count, total_amount, avg_amount
                ORDER BY total_amount DESC
                """
                
                accounts = graph.execute_custom_query(query)
                
                self.print_section("Account Overview")
                for i, account in enumerate(accounts, 1):
                    print(f"{i}. {account['account_name']:25s} ({account['account_type']})")
                    print(f"   ID: {account['account_id']}")
                    print(f"   Transactions: {account['transaction_count']:3d} - Total: ${account['total_amount']:8.2f} - Avg: ${account['avg_amount']:6.2f}")
                
                # Category breakdown by account
                if len(accounts) > 1:
                    self.print_section("Category Breakdown by Account")
                    for account in accounts[:3]:  # Top 3 accounts
                        print(f"\n🏦 {account['account_name']}:")
                        
                        query = """
                        MATCH (a:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t:Transaction)-[:IN_CATEGORY]->(c:Category)
                        RETURN c.name as category, count(t) as count, sum(t.amount) as total
                        ORDER BY total DESC
                        LIMIT 5
                        """
                        
                        categories = graph.execute_custom_query(query, {'account_id': account['account_id']})
                        for cat in categories:
                            print(f"   • {cat['category']:15s} ${cat['total']:8.2f} ({cat['count']} txns)")
                
                return True
        
        except Exception as e:
            print(f"❌ Account comparison error: {e}")
            return False
    
    def temporal_analysis(self):
        """Analyze spending patterns over time."""
        self.print_header("TEMPORAL SPENDING ANALYSIS")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                
                # Weekly spending patterns
                self.print_section("Weekly Spending Patterns")
                query = """
                MATCH (t:Transaction)
                WITH t, date.truncate('week', t.date) as week
                RETURN week, count(t) as transaction_count, sum(t.amount) as total_amount
                ORDER BY week DESC
                LIMIT 8
                """
                
                weekly_data = graph.execute_custom_query(query)
                for week in weekly_data:
                    week_str = str(week['week'])[:10]
                    print(f"{week_str}: ${week['total_amount']:8.2f} ({week['transaction_count']:3d} txns)")
                
                # Day of week analysis
                self.print_section("Day of Week Analysis")
                query = """
                MATCH (t:Transaction)
                WITH t, 
                     CASE date.dayOfWeek(t.date)
                       WHEN 1 THEN 'Monday'
                       WHEN 2 THEN 'Tuesday'
                       WHEN 3 THEN 'Wednesday'
                       WHEN 4 THEN 'Thursday'
                       WHEN 5 THEN 'Friday'
                       WHEN 6 THEN 'Saturday'
                       WHEN 7 THEN 'Sunday'
                     END as day_name
                RETURN day_name, count(t) as transaction_count, sum(t.amount) as total_amount, avg(t.amount) as avg_amount
                ORDER BY 
                  CASE day_name
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                  END
                """
                
                daily_patterns = graph.execute_custom_query(query)
                for day in daily_patterns:
                    print(f"{day['day_name']:10s}: ${day['total_amount']:8.2f} ({day['transaction_count']:3d} txns) - Avg: ${day['avg_amount']:6.2f}")
                
                return True
        
        except Exception as e:
            print(f"❌ Temporal analysis error: {e}")
            return False
    
    def export_insights(self, output_path: str = "/tmp/transaction_insights.json"):
        """Export comprehensive insights to JSON."""
        self.print_header("EXPORTING INSIGHTS")
        
        try:
            with TransactionGraphDB(self.neo4j_uri, self.neo4j_username, self.neo4j_password) as graph:
                
                insights = {
                    'generated_at': datetime.now().isoformat(),
                    'database_stats': graph.get_database_stats(),
                    'spending_by_category': graph.get_spending_by_category(90),
                    'top_merchants': graph.get_merchant_analysis(25),
                    'monthly_trends': graph.get_spending_trends(),
                    'anomalies': graph.detect_anomalies(2.0),
                    'account_summaries': []
                }
                
                # Get account summaries
                query = "MATCH (a:Account) RETURN DISTINCT a.account_id as account_id"
                accounts = graph.execute_custom_query(query)
                
                for account in accounts:
                    account_id = account['account_id']
                    summary = graph.get_account_summary(account_id)
                    if summary:
                        insights['account_summaries'].append(summary)
                
                # Add custom analytics
                insights['custom_analytics'] = {
                    'total_spending': sum(cat['total_amount'] for cat in insights['spending_by_category']),
                    'average_transaction': sum(cat['total_amount'] for cat in insights['spending_by_category']) / 
                                          sum(cat['transaction_count'] for cat in insights['spending_by_category']),
                    'most_active_category': max(insights['spending_by_category'], key=lambda x: x['transaction_count'])['category'],
                    'highest_spending_category': max(insights['spending_by_category'], key=lambda x: x['total_amount'])['category']
                }
                
                # Save insights
                with open(output_path, 'w') as f:
                    json.dump(insights, f, indent=2, default=str)
                
                print(f"✅ Insights exported to: {output_path}")
                print(f"📊 Data includes:")
                print(f"   • {len(insights['spending_by_category'])} spending categories")
                print(f"   • {len(insights['top_merchants'])} merchant analyses")
                print(f"   • {len(insights['monthly_trends'])} monthly data points")
                print(f"   • {len(insights['anomalies'])} detected anomalies")
                print(f"   • {len(insights['account_summaries'])} account summaries")
                
                return True
        
        except Exception as e:
            print(f"❌ Export error: {e}")
            return False

def main():
    """Main interactive dashboard."""
    dashboard = TransactionAnalyticsDashboard()
    
    while True:
        print("\n" + "="*60)
        print("  TRANSACTION GRAPH ANALYTICS DASHBOARD")
        print("="*60)
        print("1. 📊 Dashboard Overview")
        print("2. 📂 Category Deep Dive")
        print("3. 🏪 Merchant Relationship Analysis")
        print("4. 💳 Account Comparison")
        print("5. ⏰ Temporal Analysis")
        print("6. 📤 Export Insights")
        print("7. 🚪 Exit")
        
        choice = input("\nSelect option (1-7): ").strip()
        
        if choice == '1':
            dashboard.dashboard_overview()
        elif choice == '2':
            # First show categories, then ask for specific one
            dashboard.category_deep_dive()
            category = input("\nEnter category name for deep dive (or press Enter to skip): ").strip()
            if category:
                dashboard.category_deep_dive(category)
        elif choice == '3':
            dashboard.merchant_relationship_analysis()
        elif choice == '4':
            dashboard.account_comparison()
        elif choice == '5':
            dashboard.temporal_analysis()
        elif choice == '6':
            output_path = input("Enter output path (default: /tmp/transaction_insights.json): ").strip()
            if not output_path:
                output_path = "/tmp/transaction_insights.json"
            dashboard.export_insights(output_path)
        elif choice == '7':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1-7.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
