#!/bin/bash

# DHI Transaction Analytics - Production Deployment Script
set -e

echo "🚀 DHI Transaction Analytics - Production Deployment"
echo "=================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check environment variables
if [ -z "$PLAID_CLIENT_ID" ] || [ -z "$PLAID_SECRET" ]; then
    echo "⚠️  Warning: Plaid API credentials not set. Set PLAID_CLIENT_ID and PLAID_SECRET environment variables."
    echo "   For production, also set PLAID_ENV=production"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p data/uploads data/audio_uploads logs sql monitoring/grafana/{dashboards,provisioning}
mkdir -p frontend/{uploads,media,audio} ssl

# Create environment file
if [ ! -f .env ]; then
    echo "📄 Creating .env file..."
    cat > .env << EOF
# Plaid API Configuration
PLAID_CLIENT_ID=${PLAID_CLIENT_ID:-your_plaid_client_id}
PLAID_SECRET=${PLAID_SECRET:-your_plaid_secret}
PLAID_ENV=${PLAID_ENV:-sandbox}

# Database Configuration
POSTGRES_DB=dhi_analytics
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password_$(openssl rand -hex 8)

# Neo4j Configuration
NEO4J_USER=neo4j
NEO4J_PASSWORD=secure_password_$(openssl rand -hex 8)

# LLM API Keys (optional)
OPENAI_API_KEY=${OPENAI_API_KEY:-}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}

# Security
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)
EOF
    echo "✅ Environment file created. Please review and update .env file."
fi

# Create database initialization script
echo "🗄️  Creating database initialization script..."
cat > sql/init.sql << 'EOF'
-- DHI Analytics Database Initialization
CREATE DATABASE IF NOT EXISTS dhi_analytics;

-- Create tables for transaction data
CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR(255) PRIMARY KEY,
    account_name VARCHAR(255) NOT NULL,
    account_type VARCHAR(100),
    balance DECIMAL(15,2),
    institution_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(255) PRIMARY KEY,
    account_id VARCHAR(255),
    amount DECIMAL(15,2) NOT NULL,
    date DATE NOT NULL,
    merchant_name VARCHAR(255),
    category VARCHAR(255),
    subcategory VARCHAR(255),
    description TEXT,
    location JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    INDEX idx_account_date (account_id, date),
    INDEX idx_category (category),
    INDEX idx_merchant (merchant_name),
    INDEX idx_amount (amount)
);

-- Create tables for LLM query history
CREATE TABLE IF NOT EXISTS llm_queries (
    query_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    query_text TEXT NOT NULL,
    query_type VARCHAR(100),
    database_used VARCHAR(255),
    generated_query TEXT,
    execution_time DECIMAL(10,3),
    success BOOLEAN,
    result_count INTEGER,
    confidence_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create tables for database connections
CREATE TABLE IF NOT EXISTS database_connections (
    connection_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database_name VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    is_active BOOLEAN DEFAULT FALSE,
    last_connected TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_amount ON transactions(amount);
CREATE INDEX idx_llm_queries_user ON llm_queries(user_id);
CREATE INDEX idx_llm_queries_created ON llm_queries(created_at);
EOF

# Create monitoring configuration
echo "📊 Creating monitoring configuration..."
cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'dhi-app'
    static_configs:
      - targets: ['dhi-app:8081']
    metrics_path: '/api/metrics'
    scrape_interval: 30s

  - job_name: 'dhi-api' 
    static_configs:
      - targets: ['dhi-app:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:7474']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
EOF

# Build and start services
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.production.yml build

echo "🚀 Starting services..."
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8081/api/health >/dev/null 2>&1; then
        echo "✅ DHI Analytics Dashboard is ready!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Services failed to start properly. Check logs with: docker-compose -f docker-compose.production.yml logs"
        exit 1
    fi
    
    echo "⏳ Attempt $attempt/$max_attempts - waiting for services..."
    sleep 10
    ((attempt++))
done

# Display success message
echo ""
echo "🎉 DHI Transaction Analytics deployed successfully!"
echo "=================================================="
echo ""
echo "📱 Dashboard:     http://localhost:8081"
echo "🔗 API:           http://localhost:8080"
echo "🗄️  PostgreSQL:   localhost:5432"
echo "📊 Neo4j:         http://localhost:7474"
echo "🔴 Redis:         localhost:6379"
echo ""
echo "Optional Services:"
echo "📈 Prometheus:    http://localhost:9090 (--profile monitoring)"
echo "📊 Grafana:       http://localhost:3000 (--profile monitoring)"
echo ""
echo "🔐 To enable monitoring: docker-compose -f docker-compose.production.yml --profile monitoring up -d"
echo ""
echo "📋 To view logs: docker-compose -f docker-compose.production.yml logs -f"
echo "🛑 To stop: docker-compose -f docker-compose.production.yml down"
echo ""

# Show next steps for Plaid production
if [ "$PLAID_ENV" = "production" ]; then
    echo "🏦 PLAID PRODUCTION SETUP:"
    echo "========================"
    echo "1. Ensure you have production Plaid credentials"
    echo "2. Update .env file with production values"
    echo "3. Configure SSL certificates in ssl/ directory"
    echo "4. Update nginx.conf for your domain"
    echo "5. Set up proper firewall rules"
    echo "6. Configure backup strategies"
    echo ""
else
    echo "🧪 DEVELOPMENT/SANDBOX MODE"
    echo "=========================="
    echo "Currently running in ${PLAID_ENV} mode."
    echo "To switch to production:"
    echo "1. Set PLAID_ENV=production in .env"
    echo "2. Update Plaid credentials for production"
    echo "3. Follow production deployment checklist"
    echo ""
fi

echo "✅ Deployment complete!"
