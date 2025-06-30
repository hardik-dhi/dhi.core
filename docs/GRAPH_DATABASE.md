# Transaction Graph Database Documentation

## Overview

This document describes the graph database layer for transaction analytics using Neo4j. The system creates relationships between transactions, accounts, merchants, and categories to enable advanced analytical queries that would be difficult or impossible with traditional relational databases.

## Architecture

### Graph Schema

The graph database uses the following node types and relationships:

```
(Account)-[:HAS_TRANSACTION]->(Transaction)-[:IN_CATEGORY]->(Category)
                                    |
                                    v
                             [:AT_MERCHANT]
                                    |
                                    v
                                (Merchant)
```

#### Node Types

1. **Transaction**
   - Properties: transaction_id, amount, date, name, category, subcategory, merchant_name, location, account_id, created_at, updated_at
   - Primary node containing transaction details

2. **Account** 
   - Properties: account_id, name, type, subtype, institution_name, mask
   - Represents bank accounts

3. **Merchant**
   - Properties: name, category, location
   - Represents transaction merchants/vendors

4. **Category**
   - Properties: name, parent_category
   - Represents spending categories

#### Relationships

- `HAS_TRANSACTION`: Account → Transaction
- `IN_CATEGORY`: Transaction → Category  
- `AT_MERCHANT`: Transaction → Merchant

## Installation and Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Neo4j Python driver

### Quick Setup

1. **Start Neo4j Database:**
   ```bash
   cd /home/hardik/dhi.core
   ./scripts/setup_neo4j.sh setup
   ```

2. **Access Neo4j Browser:**
   - URL: http://localhost:7474
   - Username: neo4j
   - Password: dhi_password_123

3. **Verify Installation:**
   ```bash
   ./scripts/setup_neo4j.sh test
   ```

### Manual Setup Steps

1. **Start Neo4j:**
   ```bash
   docker-compose -f docker-compose.neo4j.yml up -d
   ```

2. **Initialize Database:**
   ```bash
   python3 scripts/transaction_graph_manager.py setup
   ```

3. **Load Data:**
   ```bash
   python3 scripts/transaction_graph_manager.py load
   ```

## Usage

### Command Line Tools

#### Transaction Graph Manager
```bash
python3 scripts/transaction_graph_manager.py [command]

Commands:
  setup         - Initialize database with indexes
  load          - Load data from Plaid API
  analyze       - Run spending analysis
  anomalies     - Detect transaction anomalies  
  similar       - Find similar transactions
  account       - Get account summary
  query         - Execute custom Cypher query
  export        - Export data to JSON/CSV
  clear         - Clear all database data
```

#### Analytics Dashboard
```bash
python3 scripts/analytics_dashboard.py
```
Interactive dashboard with:
- Database overview
- Category deep dives
- Merchant relationship analysis
- Account comparisons
- Temporal analysis
- Data export

#### Advanced Graph Queries
```bash
python3 scripts/advanced_graph_queries.py
```
Demonstrates advanced analytics:
- Spending pattern detection
- Transaction clustering
- Merchant network analysis
- Unusual sequence detection
- Spending velocity analysis
- Category transition patterns

### Neo4j Browser Queries

Access the Neo4j browser at http://localhost:7474 and run these sample queries:

#### Basic Exploration
```cypher
// Show database schema
CALL db.schema.visualization()

// Count all nodes and relationships
MATCH (n) RETURN labels(n) as NodeType, count(n) as Count

// Show sample transactions
MATCH (t:Transaction) RETURN t LIMIT 10
```

#### Spending Analysis
```cypher
// Top spending categories
MATCH (t:Transaction)-[:IN_CATEGORY]->(c:Category)
RETURN c.name as Category, 
       count(t) as Transactions, 
       sum(t.amount) as TotalAmount
ORDER BY TotalAmount DESC

// Monthly spending trends
MATCH (t:Transaction)
RETURN date.truncate('month', t.date) as Month,
       count(t) as Transactions,
       sum(t.amount) as TotalSpending
ORDER BY Month DESC

// Account spending comparison
MATCH (a:Account)-[:HAS_TRANSACTION]->(t:Transaction)
RETURN a.name as Account,
       count(t) as Transactions,
       sum(t.amount) as TotalAmount,
       avg(t.amount) as AvgAmount
ORDER BY TotalAmount DESC
```

#### Advanced Analytics
```cypher
// Find merchants visited frequently
MATCH (m:Merchant)<-[:AT_MERCHANT]-(t:Transaction)
WITH m, count(t) as visits, sum(t.amount) as total
WHERE visits >= 3
RETURN m.name as Merchant, visits, total
ORDER BY total DESC

// Detect spending anomalies
MATCH (t:Transaction)-[:IN_CATEGORY]->(c:Category)
WITH c.name as category, avg(t.amount) as avgAmount, stdev(t.amount) as stdDev
MATCH (t2:Transaction)-[:IN_CATEGORY]->(c2:Category {name: category})
WHERE abs(t2.amount - avgAmount) > (2 * stdDev)
RETURN t2.transaction_id, t2.amount, t2.name, category, avgAmount
ORDER BY abs(t2.amount - avgAmount) DESC

// Find similar transactions
MATCH (t1:Transaction {transaction_id: 'target_transaction_id'})
MATCH (t2:Transaction)
WHERE t1 <> t2 
AND (t1.merchant_name = t2.merchant_name OR t1.category = t2.category)
RETURN t2.transaction_id, t2.name, t2.amount, t2.merchant_name
LIMIT 10
```

## API Reference

### TransactionGraphDB Class

#### Core Methods

**`__init__(uri, username, password)`**
- Initialize connection to Neo4j database
- Default: bolt://localhost:7687, neo4j/dhi_password_123

**`create_indexes()`**
- Create performance indexes on key properties
- Run once during setup

**`clear_database()`**
- Remove all nodes and relationships
- Use with caution!

#### Data Loading

**`create_account_node(account: AccountNode)`**
- Create or update an account node

**`create_transaction_node(transaction: TransactionNode)`**
- Create transaction with all relationships

**`load_data_from_plaid_api(api_url)`**
- Load data from Plaid API service
- Creates accounts, transactions, merchants, categories

#### Analytics Methods

**`get_database_stats()`**
- Returns counts of all node types and relationships

**`get_spending_by_category(days=30)`**
- Spending breakdown by category for last N days

**`get_merchant_analysis(limit=10)`**
- Top merchants by transaction volume and amount

**`get_spending_trends(account_id=None)`**
- Monthly spending trends, optionally filtered by account

**`detect_anomalies(threshold_multiplier=2.0)`**
- Find transactions that deviate from normal patterns

**`find_similar_transactions(transaction_id, similarity_threshold=0.8)`**
- Find transactions similar to a given transaction

**`get_account_summary(account_id)`**
- Comprehensive summary for an account

**`execute_custom_query(query, parameters=None)`**
- Execute arbitrary Cypher queries

## Advanced Use Cases

### 1. Fraud Detection
```python
# Detect unusual spending patterns
graph.detect_anomalies(threshold_multiplier=3.0)

# Find rapid transaction sequences
query = """
MATCH (a:Account)-[:HAS_TRANSACTION]->(t1:Transaction)
MATCH (a)-[:HAS_TRANSACTION]->(t2:Transaction)
WHERE t1.date < t2.date 
AND duration.between(t1.date, t2.date).minutes <= 5
AND t1.amount > 100 AND t2.amount > 100
RETURN t1, t2, duration.between(t1.date, t2.date).minutes as gap
"""
results = graph.execute_custom_query(query)
```

### 2. Spending Behavior Analysis
```python
# Analyze day-of-week spending patterns
query = """
MATCH (t:Transaction)
RETURN date.dayOfWeek(t.date) as dayOfWeek,
       avg(t.amount) as avgAmount,
       count(t) as transactionCount
ORDER BY dayOfWeek
"""
patterns = graph.execute_custom_query(query)
```

### 3. Merchant Relationship Mining
```python
# Find merchants often visited together
query = """
MATCH (a:Account)-[:HAS_TRANSACTION]->(t1:Transaction)-[:AT_MERCHANT]->(m1:Merchant)
MATCH (a)-[:HAS_TRANSACTION]->(t2:Transaction)-[:AT_MERCHANT]->(m2:Merchant)
WHERE m1 <> m2 AND abs(duration.between(t1.date, t2.date).days) <= 1
WITH m1, m2, count(*) as coOccurrence
WHERE coOccurrence >= 2
RETURN m1.name, m2.name, coOccurrence
ORDER BY coOccurrence DESC
"""
relationships = graph.execute_custom_query(query)
```

### 4. Predictive Analytics
```python
# Analyze category transition patterns
query = """
MATCH (a:Account)-[:HAS_TRANSACTION]->(t1:Transaction)-[:IN_CATEGORY]->(c1:Category)
MATCH (a)-[:HAS_TRANSACTION]->(t2:Transaction)-[:IN_CATEGORY]->(c2:Category)
WHERE t1.date < t2.date AND duration.between(t1.date, t2.date).days <= 7
WITH c1.name as fromCategory, c2.name as toCategory, count(*) as transitions
RETURN fromCategory, toCategory, transitions
ORDER BY transitions DESC
"""
transitions = graph.execute_custom_query(query)
```

## Data Export and Integration

### Export Options

1. **JSON Export:**
   ```bash
   python3 scripts/transaction_graph_manager.py export json /path/to/output.json
   ```

2. **CSV Export:**
   ```bash
   python3 scripts/transaction_graph_manager.py export csv /path/to/output.csv
   ```

3. **Dashboard Export:**
   ```bash
   python3 scripts/analytics_dashboard.py
   # Select option 6 for comprehensive insights export
   ```

### Integration with External Tools

#### Jupyter Notebooks
```python
import sys
sys.path.append('/home/hardik/dhi.core')
from dhi_core.graph.transaction_graph import TransactionGraphDB

# Connect and analyze
with TransactionGraphDB() as graph:
    categories = graph.get_spending_by_category(90)
    # Convert to pandas DataFrame for analysis
    import pandas as pd
    df = pd.DataFrame(categories)
```

#### Power BI / Tableau
- Export data as CSV/JSON
- Use Neo4j's JDBC driver for direct connection
- Create visualizations from exported analytics

## Performance Optimization

### Indexing Strategy

The system automatically creates indexes on:
- Transaction.transaction_id
- Account.account_id  
- Merchant.name
- Category.name
- Transaction.date
- Transaction.amount
- Transaction.category

### Query Optimization Tips

1. **Use indexes** - Always filter on indexed properties first
2. **Limit results** - Use LIMIT clause for large datasets
3. **Profile queries** - Use `PROFILE` in Neo4j browser
4. **Avoid cartesian products** - Use proper relationship patterns

### Memory Configuration

Neo4j is configured with:
- Heap size: 512MB initial, 2GB max
- Page cache: 1GB
- Adjust in docker-compose.neo4j.yml for larger datasets

## Troubleshooting

### Common Issues

1. **Connection Failed:**
   ```bash
   # Check if Neo4j is running
   docker ps | grep neo4j
   
   # Restart if needed
   ./scripts/setup_neo4j.sh restart
   ```

2. **Out of Memory:**
   - Increase heap size in docker-compose.neo4j.yml
   - Use LIMIT clauses in queries
   - Create more specific indexes

3. **Slow Queries:**
   - Use PROFILE to analyze query execution
   - Ensure proper indexes exist
   - Optimize relationship patterns

4. **Data Loading Issues:**
   - Verify Plaid API is running: `curl http://localhost:8080/health`
   - Check transaction_graph_manager.py logs
   - Ensure proper data format

### Maintenance Commands

```bash
# View Neo4j logs
./scripts/setup_neo4j.sh logs

# Check database status
./scripts/setup_neo4j.sh status

# Clean and restart
./scripts/setup_neo4j.sh clean
./scripts/setup_neo4j.sh setup
```

## Security Considerations

1. **Change default password** in production
2. **Enable authentication** for Neo4j browser
3. **Use encrypted connections** (SSL/TLS)
4. **Restrict network access** to Neo4j ports
5. **Regular backups** of Neo4j data volume

## Extensions and Customization

### Adding New Node Types

1. Create dataclass in transaction_graph.py
2. Add creation method to TransactionGraphDB
3. Update loading logic
4. Create appropriate indexes

### Custom Analytics Functions

```python
def custom_analysis(self):
    query = """
    // Your custom Cypher query
    MATCH (pattern)
    RETURN results
    """
    return self.execute_custom_query(query)
```

### Integration with Other Databases

- Use APOC procedures for data import/export
- Connect to PostgreSQL with apoc.load.jdbc
- Export to external systems via REST APIs

## Support and Resources

- **Neo4j Documentation:** https://neo4j.com/docs/
- **Cypher Query Language:** https://neo4j.com/docs/cypher-manual/
- **APOC Procedures:** https://neo4j.com/docs/apoc/
- **Graph Algorithms:** https://neo4j.com/docs/graph-data-science/

For project-specific issues, check the transaction_graph_manager.py logs and ensure all dependencies are properly installed.
