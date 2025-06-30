# Plaid Integration

This directory contains the Plaid API integration for fetching bank transactions.

## Setup

1. **Get Plaid API credentials**: Sign up at [Plaid Dashboard](https://dashboard.plaid.com) and get your:
   - Client ID
   - Secret key
   - Choose environment (sandbox/development/production)

2. **Configure environment variables** in your `.env` file:
   ```bash
   PLAID_CLIENT_ID=your_client_id_here
   PLAID_SECRET=your_secret_here
   PLAID_ENVIRONMENT=sandbox
   PLAID_PRODUCTS=transactions
   PLAID_COUNTRY_CODES=US
   ```

3. **Install dependencies**:
   ```bash
   make install  # or pip install plaid-python
   ```

## Usage

### 1. Command Line Interface

The script provides a CLI for managing Plaid integration:

```bash
# Create a link token (needed for frontend integration)
python scripts/plaid_script.py create-link-token user123

# Link a bank account (after user completes Plaid Link flow)
python scripts/plaid_script.py link-account user123 public-sandbox-abc123

# Fetch transactions for an access token
python scripts/plaid_script.py fetch-transactions access-sandbox-xyz789 --days-back 30

# Get stored transactions for a user
python scripts/plaid_script.py get-transactions user123 --limit 50

# Sync all linked accounts
python scripts/plaid_script.py sync-all --days-back 7

# List all linked accounts
python scripts/plaid_script.py list-accounts

# Show transaction summary
python scripts/plaid_script.py summary user123 --days-back 30
```

### 2. Using the Makefile

The Makefile includes convenient targets for Plaid operations:

```bash
# Create link token
make plaid-link-token USER_ID=user123

# Sync all accounts
make plaid-sync

# List accounts
make plaid-accounts

# Show transactions
make plaid-transactions USER_ID=user123

# Show summary
make plaid-summary USER_ID=user123
```

### 3. REST API Endpoints

The integration adds these endpoints to your FastAPI application:

- `POST /plaid/link-token` - Create link token
- `POST /plaid/exchange-token` - Exchange public token for access token
- `POST /plaid/fetch-transactions` - Fetch transactions from Plaid
- `GET /plaid/transactions/{user_id}` - Get stored transactions
- `GET /plaid/accounts/{user_id}` - Get linked accounts
- `POST /plaid/sync-transactions/{access_token}` - Sync recent transactions
- `GET /plaid/transaction-summary/{user_id}` - Get transaction summary

## Workflow

### For Development/Testing (Sandbox)

1. **Create a link token**:
   ```bash
   make plaid-link-token USER_ID=testuser
   ```

2. **Use Plaid Link** (in sandbox, you can use test credentials):
   - Username: `user_good`
   - Password: `pass_good`
   - PIN: `1234` (if required)

3. **After linking, you'll get a public token** - exchange it:
   ```bash
   python scripts/plaid_script.py link-account testuser public_token_here
   ```

4. **Fetch transactions**:
   ```bash
   make plaid-sync
   ```

5. **View your transactions**:
   ```bash
   make plaid-transactions USER_ID=testuser
   make plaid-summary USER_ID=testuser
   ```

### For Production

1. Switch to production environment in `.env`:
   ```bash
   PLAID_ENVIRONMENT=production
   ```

2. Use real bank credentials through Plaid Link

3. Same workflow as above with real data

## Database Tables

The integration creates two tables:

### `plaid_accounts`
- Stores linked bank account information
- Access tokens for API calls
- Account metadata (name, type, institution)

### `plaid_transactions`
- Stores transaction details
- Includes merchant info, categories, location
- Linked to accounts via `account_id`

## Security Notes

- **Never expose access tokens** - they provide full account access
- Store tokens securely and encrypt in production
- Use HTTPS for all API communications
- Implement proper user authentication
- Consider token rotation and expiration handling

## Error Handling

The integration includes comprehensive error handling for:
- Invalid tokens
- API rate limits
- Network issues
- Data parsing errors
- Database connection issues

## Customization

You can extend the integration by:
- Adding more Plaid products (identity, assets, liabilities)
- Implementing webhooks for real-time updates
- Adding transaction categorization logic
- Creating custom reporting and analytics
- Integrating with other financial services
