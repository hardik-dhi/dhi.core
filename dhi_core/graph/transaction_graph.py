#!/usr/bin/env python3
"""
Transaction Graph Database Layer

This module creates and manages a graph representation of financial transaction data
using Neo4j for advanced analytics and relationship-based queries.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
import logging
from dataclasses import dataclass
from decimal import Decimal

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable, AuthError
except ImportError:
    print("Warning: neo4j package not installed. Run: pip install neo4j")
    GraphDatabase = None

@dataclass
class TransactionNode:
    """Represents a transaction node in the graph."""
    transaction_id: str
    amount: float
    date: str
    name: str
    category: str
    subcategory: Optional[str] = None
    merchant_name: Optional[str] = None
    location: Optional[Dict[str, str]] = None
    account_id: str = None
    created_at: str = None
    updated_at: str = None

@dataclass
class AccountNode:
    """Represents an account node in the graph."""
    account_id: str
    name: str
    type: str
    subtype: Optional[str] = None
    institution_name: Optional[str] = None
    mask: Optional[str] = None

@dataclass
class MerchantNode:
    """Represents a merchant node in the graph."""
    name: str
    category: Optional[str] = None
    location: Optional[Dict[str, str]] = None

@dataclass
class CategoryNode:
    """Represents a category node in the graph."""
    name: str
    parent_category: Optional[str] = None

class TransactionGraphDB:
    """
    Graph database manager for financial transaction data.
    
    Creates and manages relationships between:
    - Accounts and Transactions
    - Transactions and Merchants  
    - Transactions and Categories
    - Merchants and Locations
    - Time-based patterns
    """
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 username: str = "neo4j", password: str = "password"):
        """Initialize connection to Neo4j database."""
        if GraphDatabase is None:
            raise ImportError("neo4j package not installed. Run: pip install neo4j")
        
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.logger = logging.getLogger(__name__)
        
        # Test connection
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.logger.info("Successfully connected to Neo4j")
        except (ServiceUnavailable, AuthError) as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.driver:
            self.driver.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def clear_database(self):
        """Clear all nodes and relationships. Use with caution!"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        self.logger.info("Database cleared")
    
    def create_indexes(self):
        """Create indexes for better query performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (t:Transaction) ON (t.transaction_id)",
            "CREATE INDEX IF NOT EXISTS FOR (a:Account) ON (a.account_id)",
            "CREATE INDEX IF NOT EXISTS FOR (m:Merchant) ON (m.name)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Category) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (t:Transaction) ON (t.date)",
            "CREATE INDEX IF NOT EXISTS FOR (t:Transaction) ON (t.amount)",
            "CREATE INDEX IF NOT EXISTS FOR (t:Transaction) ON (t.category)",
        ]
        
        with self.driver.session() as session:
            for index in indexes:
                session.run(index)
        
        self.logger.info("Database indexes created")
    
    def create_account_node(self, account: AccountNode) -> bool:
        """Create or update an account node."""
        query = """
        MERGE (a:Account {account_id: $account_id})
        SET a.name = $name,
            a.type = $type,
            a.subtype = $subtype,
            a.institution_name = $institution_name,
            a.mask = $mask,
            a.updated_at = datetime()
        RETURN a
        """
        
        with self.driver.session() as session:
            result = session.run(query, {
                'account_id': account.account_id,
                'name': account.name,
                'type': account.type,
                'subtype': account.subtype,
                'institution_name': account.institution_name,
                'mask': account.mask
            })
            return result.single() is not None
    
    def create_merchant_node(self, merchant: MerchantNode) -> bool:
        """Create or update a merchant node."""
        query = """
        MERGE (m:Merchant {name: $name})
        SET m.category = $category,
            m.location = $location,
            m.updated_at = datetime()
        RETURN m
        """
        
        with self.driver.session() as session:
            result = session.run(query, {
                'name': merchant.name,
                'category': merchant.category,
                'location': merchant.location
            })
            return result.single() is not None
    
    def create_category_node(self, category: CategoryNode) -> bool:
        """Create or update a category node."""
        query = """
        MERGE (c:Category {name: $name})
        SET c.parent_category = $parent_category,
            c.updated_at = datetime()
        RETURN c
        """
        
        with self.driver.session() as session:
            result = session.run(query, {
                'name': category.name,
                'parent_category': category.parent_category
            })
            return result.single() is not None
    
    def create_transaction_node(self, transaction: TransactionNode) -> bool:
        """Create or update a transaction node with all relationships."""
        
        # Create transaction node
        tx_query = """
        MERGE (t:Transaction {transaction_id: $transaction_id})
        SET t.amount = $amount,
            t.date = date($date),
            t.name = $name,
            t.category = $category,
            t.subcategory = $subcategory,
            t.merchant_name = $merchant_name,
            t.location = $location,
            t.created_at = datetime($created_at),
            t.updated_at = datetime($updated_at)
        RETURN t
        """
        
        # Create relationships
        account_rel_query = """
        MATCH (t:Transaction {transaction_id: $transaction_id})
        MATCH (a:Account {account_id: $account_id})
        MERGE (a)-[:HAS_TRANSACTION]->(t)
        """
        
        merchant_rel_query = """
        MATCH (t:Transaction {transaction_id: $transaction_id})
        MERGE (m:Merchant {name: $merchant_name})
        MERGE (t)-[:AT_MERCHANT]->(m)
        """
        
        category_rel_query = """
        MATCH (t:Transaction {transaction_id: $transaction_id})
        MERGE (c:Category {name: $category})
        MERGE (t)-[:IN_CATEGORY]->(c)
        """
        
        with self.driver.session() as session:
            # Create transaction
            result = session.run(tx_query, {
                'transaction_id': transaction.transaction_id,
                'amount': transaction.amount,
                'date': transaction.date,
                'name': transaction.name,
                'category': transaction.category,
                'subcategory': transaction.subcategory,
                'merchant_name': transaction.merchant_name,
                'location': transaction.location,
                'created_at': transaction.created_at,
                'updated_at': transaction.updated_at
            })
            
            if result.single() is None:
                return False
            
            # Create account relationship
            if transaction.account_id:
                session.run(account_rel_query, {
                    'transaction_id': transaction.transaction_id,
                    'account_id': transaction.account_id
                })
            
            # Create merchant relationship
            if transaction.merchant_name:
                session.run(merchant_rel_query, {
                    'transaction_id': transaction.transaction_id,
                    'merchant_name': transaction.merchant_name
                })
            
            # Create category relationship
            if transaction.category:
                session.run(category_rel_query, {
                    'transaction_id': transaction.transaction_id,
                    'category': transaction.category
                })
            
            return True
    
    def load_data_from_plaid_api(self, plaid_api_url: str = "http://localhost:8080"):
        """Load transaction and account data from Plaid API."""
        import requests
        
        try:
            # Get accounts
            accounts_response = requests.get(f"{plaid_api_url}/accounts")
            accounts_data = accounts_response.json()["data"]
            
            # Get transactions
            transactions_response = requests.get(f"{plaid_api_url}/transactions")
            transactions_data = transactions_response.json()["data"]
            
            self.logger.info(f"Loading {len(accounts_data)} accounts and {len(transactions_data)} transactions")
            
            # Create account nodes
            for acc_data in accounts_data:
                account = AccountNode(
                    account_id=acc_data['account_id'],
                    name=acc_data['name'],
                    type=acc_data['type'],
                    subtype=acc_data.get('subtype'),
                    institution_name=acc_data.get('institution_name'),
                    mask=acc_data.get('mask')
                )
                self.create_account_node(account)
            
            # Create transaction nodes
            for tx_data in transactions_data:
                transaction = TransactionNode(
                    transaction_id=tx_data['transaction_id'],
                    amount=float(tx_data['amount']),
                    date=tx_data['date'],
                    name=tx_data['name'],
                    category=tx_data.get('category', 'Other'),
                    subcategory=tx_data.get('subcategory'),
                    merchant_name=tx_data.get('merchant_name'),
                    location=tx_data.get('location'),
                    account_id=tx_data['account_id'],
                    created_at=tx_data.get('created_at'),
                    updated_at=tx_data.get('updated_at')
                )
                self.create_transaction_node(transaction)
            
            self.logger.info("Data loading completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            return False
    
    def get_account_summary(self, account_id: str) -> Dict[str, Any]:
        """Get comprehensive summary for an account."""
        query = """
        MATCH (a:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t:Transaction)
        RETURN a.name as account_name,
               a.type as account_type,
               a.institution_name as institution,
               COUNT(t) as transaction_count,
               SUM(t.amount) as total_amount,
               AVG(t.amount) as avg_amount,
               MIN(t.date) as earliest_transaction,
               MAX(t.date) as latest_transaction,
               COLLECT(DISTINCT t.category) as categories
        """
        
        with self.driver.session() as session:
            result = session.run(query, {'account_id': account_id})
            return dict(result.single()) if result.single() else {}
    
    def get_spending_by_category(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get spending breakdown by category for the last N days."""
        query = """
        MATCH (t:Transaction)-[:IN_CATEGORY]->(c:Category)
        WHERE t.date >= date() - duration({days: $days})
        RETURN c.name as category,
               COUNT(t) as transaction_count,
               SUM(t.amount) as total_amount,
               AVG(t.amount) as avg_amount
        ORDER BY total_amount DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, {'days': days})
            return [dict(record) for record in result]
    
    def get_merchant_analysis(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top merchants by transaction volume and amount."""
        query = """
        MATCH (t:Transaction)-[:AT_MERCHANT]->(m:Merchant)
        RETURN m.name as merchant,
               COUNT(t) as transaction_count,
               SUM(t.amount) as total_amount,
               AVG(t.amount) as avg_amount,
               COLLECT(DISTINCT t.category) as categories
        ORDER BY total_amount DESC
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(query, {'limit': limit})
            return [dict(record) for record in result]
    
    def find_similar_transactions(self, transaction_id: str, 
                                similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Find transactions similar to a given transaction."""
        query = """
        MATCH (t1:Transaction {transaction_id: $transaction_id})
        MATCH (t2:Transaction)
        WHERE t1 <> t2
        AND (
            t1.merchant_name = t2.merchant_name
            OR t1.category = t2.category
            OR ABS(t1.amount - t2.amount) < 10.0
        )
        RETURN t2.transaction_id as transaction_id,
               t2.name as name,
               t2.amount as amount,
               t2.date as date,
               t2.category as category,
               t2.merchant_name as merchant,
               CASE 
                   WHEN t1.merchant_name = t2.merchant_name THEN 1.0
                   ELSE 0.0
               END +
               CASE 
                   WHEN t1.category = t2.category THEN 0.5
                   ELSE 0.0
               END +
               CASE 
                   WHEN ABS(t1.amount - t2.amount) < 5.0 THEN 0.3
                   ELSE 0.0
               END as similarity_score
        ORDER BY similarity_score DESC
        LIMIT 10
        """
        
        with self.driver.session() as session:
            result = session.run(query, {'transaction_id': transaction_id})
            return [dict(record) for record in result 
                   if record['similarity_score'] >= similarity_threshold]
    
    def get_spending_trends(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get monthly spending trends."""
        base_query = """
        MATCH (t:Transaction)
        {account_filter}
        RETURN date.truncate('month', t.date) as month,
               COUNT(t) as transaction_count,
               SUM(t.amount) as total_amount,
               AVG(t.amount) as avg_amount
        ORDER BY month DESC
        """
        
        if account_id:
            query = base_query.format(
                account_filter="MATCH (a:Account {account_id: $account_id})-[:HAS_TRANSACTION]->(t)"
            )
            params = {'account_id': account_id}
        else:
            query = base_query.format(account_filter="")
            params = {}
        
        with self.driver.session() as session:
            result = session.run(query, params)
            return [dict(record) for record in result]
    
    def detect_anomalies(self, threshold_multiplier: float = 2.0) -> List[Dict[str, Any]]:
        """Detect transaction anomalies based on amount and frequency."""
        query = """
        MATCH (t:Transaction)-[:IN_CATEGORY]->(c:Category)
        WITH c.name as category, 
             AVG(t.amount) as avg_amount, 
             STDEV(t.amount) as stdev_amount,
             COUNT(t) as transaction_count
        MATCH (t2:Transaction)-[:IN_CATEGORY]->(c2:Category {name: category})
        WHERE ABS(t2.amount - avg_amount) > ($threshold * stdev_amount)
        RETURN t2.transaction_id as transaction_id,
               t2.name as name,
               t2.amount as amount,
               t2.date as date,
               category,
               avg_amount,
               ABS(t2.amount - avg_amount) / stdev_amount as anomaly_score
        ORDER BY anomaly_score DESC
        LIMIT 20
        """
        
        with self.driver.session() as session:
            result = session.run(query, {'threshold': threshold_multiplier})
            return [dict(record) for record in result]
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        queries = {
            'transactions': "MATCH (t:Transaction) RETURN count(t) as count",
            'accounts': "MATCH (a:Account) RETURN count(a) as count",
            'merchants': "MATCH (m:Merchant) RETURN count(m) as count",
            'categories': "MATCH (c:Category) RETURN count(c) as count",
            'relationships': "MATCH ()-[r]->() RETURN count(r) as count"
        }
        
        stats = {}
        with self.driver.session() as session:
            for name, query in queries.items():
                result = session.run(query)
                stats[name] = result.single()['count']
        
        return stats
    
    def execute_custom_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a custom Cypher query."""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
