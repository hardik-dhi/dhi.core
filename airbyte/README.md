# Airbyte + Plaid Integration

This directory contains the configuration and setup for syncing Plaid transaction data to PostgreSQL using Airbyte.

## Overview

The integration consists of:
1. **Custom Plaid API Service** - Exposes Plaid data in Airbyte-compatible format
2. **Airbyte Configuration** - HTTP source connector and PostgreSQL destination
3. **Automated Setup Scripts** - For easy deployment and management

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Plaid API     │    │  Custom Plaid   │    │    Airbyte      │
│   (External)    │ -> │  API Service    │ -> │   (HTTP Source) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        v
                                              ┌─────────────────┐
                                              │   PostgreSQL    │
                                              │  (Destination)  │
                                              └─────────────────┘
```

## Quick Start

### Prerequisites

1. **Docker & Docker Compose** installed
2. **Plaid API credentials** configured in `.env`
3. **PostgreSQL database** running and accessible
4. **Plaid accounts linked** (use `make plaid-link-token` and `make plaid-sync`)

### 1. Check Dependencies

```bash
make airbyte-check
```

### 2. Initialize Complete Setup

```bash
make airbyte-init
```

This will:
- Start all Airbyte services
- Start the custom Plaid API service
- Configure source and destination connections
- Set up automated sync schedule

### 3. Access Airbyte UI

Visit [http://localhost:8000](http://localhost:8000) to access the Airbyte web interface.

## Manual Setup

If you prefer step-by-step setup:

### 1. Start Services

```bash
make airbyte-start
```

### 2. Configure Connections

```bash
make airbyte-setup
```

### 3. Trigger Initial Sync

```bash
make airbyte-sync
```

## Configuration Files

### `docker-compose.yml`
Complete Airbyte stack with custom Plaid API service:
- **airbyte-webapp** - Web UI (port 8000)
- **airbyte-server** - API server (port 8001)
- **airbyte-worker** - Sync worker
- **airbyte-db** - Internal PostgreSQL (port 5433)
- **plaid-api** - Custom Plaid API service (port 8080)

### `plaid_api_service.py`
FastAPI service that exposes Plaid data with endpoints:
- `GET /accounts` - List all linked accounts
- `GET /transactions` - List transactions with filtering
- `GET /transactions/incremental` - Incremental sync support
- `GET /schema/*` - Schema definitions for Airbyte
- `POST /sync/full` - Trigger full Plaid data refresh

### Source Configuration
HTTP source connector that reads from custom Plaid API:
- **Accounts Stream** - Full refresh every sync
- **Transactions Stream** - Incremental sync based on `updated_at`

### Destination Configuration
PostgreSQL destination with:
- **Schema**: `airbyte_plaid`
- **Tables**: `accounts`, `transactions`
- **Normalization**: Basic normalization enabled

## Data Schema

### Accounts Table (`airbyte_plaid.accounts`)
```sql
account_id          VARCHAR PRIMARY KEY
access_token        VARCHAR
item_id            VARCHAR
name               VARCHAR
type               VARCHAR
subtype            VARCHAR
institution_name   VARCHAR
mask               VARCHAR
created_at         TIMESTAMP
updated_at         TIMESTAMP
_airbyte_extracted_at TIMESTAMP
```

### Transactions Table (`airbyte_plaid.transactions`)
```sql
transaction_id      VARCHAR PRIMARY KEY
account_id          VARCHAR
amount              DECIMAL
date                DATE
name                VARCHAR
merchant_name       VARCHAR
category            VARCHAR
subcategory         VARCHAR
account_owner       VARCHAR
authorized_date     DATE
location            JSONB
iso_currency_code   VARCHAR
-- ... additional fields
created_at          TIMESTAMP
updated_at          TIMESTAMP
_airbyte_extracted_at TIMESTAMP
```

## Sync Configuration

- **Schedule**: Every 6 hours (configurable)
- **Accounts**: Full refresh (overwrites data)
- **Transactions**: Incremental append (based on `updated_at`)

## Management Commands

### Check Status
```bash
make airbyte-status
```

### View Logs
```bash
make airbyte-logs
```

### Trigger Manual Sync
```bash
make airbyte-sync
```

### Stop Services
```bash
make airbyte-stop
```

## Querying Synced Data

Once data is synced, you can query it from PostgreSQL:

```sql
-- View account summary
SELECT 
    name,
    type,
    institution_name,
    mask
FROM airbyte_plaid.accounts;

-- View recent transactions
SELECT 
    t.date,
    t.name,
    t.amount,
    t.category,
    a.name as account_name
FROM airbyte_plaid.transactions t
JOIN airbyte_plaid.accounts a ON t.account_id = a.account_id
ORDER BY t.date DESC
LIMIT 20;

-- Monthly spending by category
SELECT 
    t.category,
    DATE_TRUNC('month', t.date) as month,
    SUM(t.amount) as total_amount,
    COUNT(*) as transaction_count
FROM airbyte_plaid.transactions t
WHERE t.amount > 0  -- Debits (spending)
GROUP BY t.category, DATE_TRUNC('month', t.date)
ORDER BY month DESC, total_amount DESC;
```

## Troubleshooting

### Services Not Starting
- Check Docker is running: `docker ps`
- Check port conflicts: `netstat -tlnp | grep :8000`
- View logs: `make airbyte-logs`

### No Data Syncing
- Ensure Plaid accounts are linked: `make plaid-accounts`
- Trigger Plaid sync first: `make plaid-sync`
- Check Plaid API health: `curl http://localhost:8080/health`

### Connection Errors
- Verify PostgreSQL is accessible
- Check database credentials in `.env`
- Ensure schema permissions are correct

### Custom API Issues
- Check Plaid API logs: `docker logs plaid-api`
- Test endpoints manually: `curl http://localhost:8080/stats`
- Verify Plaid credentials in environment

## Advanced Configuration

### Custom Sync Schedule
Edit the connection in Airbyte UI or modify `airbyte_setup.py`:
```python
"schedule": {
    "scheduleType": "cron",
    "cronExpression": "0 */4 * * *"  # Every 4 hours
}
```

### Additional Streams
Add more endpoints to `plaid_api_service.py`:
```python
@app.get("/balances")
async def get_balances():
    # Implement balance data endpoint
    pass
```

### Custom Transformations
Enable dbt in Airbyte for advanced transformations:
1. Enable dbt normalization in destination
2. Create custom transformation models
3. Schedule transformation runs

## Monitoring

### Airbyte UI Monitoring
- **Connections** - View sync status and history
- **Jobs** - Monitor running and completed syncs
- **Logs** - Debug sync issues

### Custom Monitoring
Monitor the Plaid API service:
```bash
# Health check
curl http://localhost:8080/health

# Data statistics
curl http://localhost:8080/stats

# Recent transactions count
curl "http://localhost:8080/transactions?limit=1" | jq '.total_count'
```

## Production Considerations

### Security
- Remove `access_token` from accounts API response
- Use environment variables for all credentials
- Enable SSL/TLS for all connections
- Implement proper authentication for API endpoints

### Performance
- Add database indexes on frequently queried columns
- Configure connection pooling
- Monitor resource usage and scale accordingly
- Consider partitioning large transaction tables

### Reliability
- Set up proper backup strategies
- Monitor sync failures and set up alerts
- Implement retry logic for failed syncs
- Use persistent volumes for Airbyte data

## Support

For issues and questions:
1. Check the logs: `make airbyte-logs`
2. Review Airbyte documentation: https://docs.airbyte.com
3. Check Plaid API status: https://status.plaid.com
4. Review the source code in this directory
