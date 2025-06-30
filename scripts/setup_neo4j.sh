#!/bin/bash
"""
Neo4j Graph Database Setup Script

This script sets up and manages the Neo4j database for transaction analytics.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="/home/hardik/dhi.core"
NEO4J_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.neo4j.yml"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker Desktop."
        exit 1
    fi
    
    print_success "Docker is available and running"
}

setup_neo4j() {
    print_status "Setting up Neo4j database..."
    
    cd "$PROJECT_ROOT"
    
    # Start Neo4j
    docker-compose -f "$NEO4J_COMPOSE_FILE" up -d
    
    print_status "Waiting for Neo4j to start (this may take a minute)..."
    sleep 30
    
    # Wait for Neo4j to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:7474 > /dev/null 2>&1; then
            print_success "Neo4j is running and accessible!"
            break
        fi
        
        print_status "Attempt $attempt/$max_attempts - waiting for Neo4j..."
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_error "Neo4j failed to start within expected time"
        exit 1
    fi
}

test_connection() {
    print_status "Testing Neo4j connection..."
    
    cd "$PROJECT_ROOT"
    python3 -c "
import sys
sys.path.append('.')
from scripts.transaction_graph_manager import TransactionGraphManager

manager = TransactionGraphManager(
    neo4j_uri='bolt://localhost:7687',
    neo4j_username='neo4j', 
    neo4j_password='dhi_password_123'
)

if manager.check_connection():
    print('✅ Successfully connected to Neo4j!')
else:
    print('❌ Failed to connect to Neo4j')
    sys.exit(1)
"
}

initialize_database() {
    print_status "Initializing database schema and indexes..."
    
    cd "$PROJECT_ROOT"
    python3 -c "
import sys
sys.path.append('.')
from scripts.transaction_graph_manager import TransactionGraphManager

manager = TransactionGraphManager(
    neo4j_uri='bolt://localhost:7687',
    neo4j_username='neo4j', 
    neo4j_password='dhi_password_123'
)

if manager.setup_database():
    print('✅ Database initialized successfully!')
else:
    print('❌ Failed to initialize database')
    sys.exit(1)
"
}

load_sample_data() {
    print_status "Loading transaction data from Plaid API..."
    
    # First check if Plaid API is available
    if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
        print_warning "Plaid API is not running. Starting it first..."
        cd "$PROJECT_ROOT/airbyte"
        docker-compose up -d plaid-api-service
        sleep 10
    fi
    
    cd "$PROJECT_ROOT"
    python3 -c "
import sys
sys.path.append('.')
from scripts.transaction_graph_manager import TransactionGraphManager

manager = TransactionGraphManager(
    neo4j_uri='bolt://localhost:7687',
    neo4j_username='neo4j', 
    neo4j_password='dhi_password_123'
)

if manager.load_data():
    print('✅ Sample data loaded successfully!')
else:
    print('❌ Failed to load sample data')
    sys.exit(1)
"
}

show_analytics() {
    print_status "Running sample analytics..."
    
    cd "$PROJECT_ROOT"
    python3 -c "
import sys
sys.path.append('.')
from scripts.transaction_graph_manager import TransactionGraphManager

manager = TransactionGraphManager(
    neo4j_uri='bolt://localhost:7687',
    neo4j_username='neo4j', 
    neo4j_password='dhi_password_123'
)

print('\\n📊 Running spending analysis...')
manager.analyze_spending(30)

print('\\n🔍 Detecting anomalies...')
manager.detect_anomalies(2.0)
"
}

show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  setup     - Complete setup: start Neo4j, initialize DB, load data"
    echo "  start     - Start Neo4j database"
    echo "  stop      - Stop Neo4j database"
    echo "  restart   - Restart Neo4j database"
    echo "  status    - Check Neo4j status"
    echo "  test      - Test database connection"
    echo "  init      - Initialize database schema"
    echo "  load      - Load sample data from Plaid API"
    echo "  analytics - Run sample analytics"
    echo "  logs      - Show Neo4j logs"
    echo "  clean     - Remove all containers and volumes"
    echo ""
    echo "Database Access:"
    echo "  Web UI:    http://localhost:7474"
    echo "  Bolt:      bolt://localhost:7687"
    echo "  Username:  neo4j"
    echo "  Password:  dhi_password_123"
}

case "${1:-}" in
    setup)
        check_docker
        setup_neo4j
        test_connection
        initialize_database
        load_sample_data
        show_analytics
        print_success "Complete setup finished! Access Neo4j at http://localhost:7474"
        ;;
    start)
        check_docker
        docker-compose -f "$NEO4J_COMPOSE_FILE" up -d
        print_success "Neo4j started"
        ;;
    stop)
        docker-compose -f "$NEO4J_COMPOSE_FILE" down
        print_success "Neo4j stopped"
        ;;
    restart)
        docker-compose -f "$NEO4J_COMPOSE_FILE" restart
        print_success "Neo4j restarted"
        ;;
    status)
        docker-compose -f "$NEO4J_COMPOSE_FILE" ps
        ;;
    test)
        test_connection
        ;;
    init)
        check_docker
        initialize_database
        ;;
    load)
        check_docker
        load_sample_data
        ;;
    analytics)
        show_analytics
        ;;
    logs)
        docker-compose -f "$NEO4J_COMPOSE_FILE" logs -f neo4j
        ;;
    clean)
        print_warning "This will remove all Neo4j data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f "$NEO4J_COMPOSE_FILE" down -v
            print_success "Neo4j cleaned"
        else
            print_status "Operation cancelled"
        fi
        ;;
    *)
        show_usage
        ;;
esac
