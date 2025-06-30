#!/bin/bash
"""
DHI Frontend Server Launcher

This script starts the frontend server for the DHI Analytics Dashboard.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="/home/hardik/dhi.core"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

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

check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check required Python packages
    python3 -c "import fastapi, uvicorn, aiofiles" 2>/dev/null || {
        print_warning "Installing required Python packages..."
        pip3 install fastapi uvicorn aiofiles python-multipart
    }
    
    print_success "Dependencies checked"
}

check_plaid_api() {
    print_status "Checking Plaid API service..."
    
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        print_success "Plaid API is running"
    else
        print_warning "Plaid API is not running. Starting it..."
        cd "$PROJECT_ROOT/airbyte"
        if [ -f "docker-compose.yml" ]; then
            docker-compose up -d plaid-api-service
            sleep 5
            
            if curl -s http://localhost:8080/health > /dev/null 2>&1; then
                print_success "Plaid API started successfully"
            else
                print_error "Failed to start Plaid API"
                exit 1
            fi
        else
            print_warning "Plaid API docker-compose.yml not found. You may need to start it manually."
        fi
    fi
}

create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p "$FRONTEND_DIR/uploads"
    mkdir -p "$FRONTEND_DIR/media"
    mkdir -p "$FRONTEND_DIR/audio"
    
    print_success "Directories created"
}

start_frontend_server() {
    print_status "Starting DHI Frontend Server..."
    
    cd "$FRONTEND_DIR"
    
    # Set environment variables
    export HOST=0.0.0.0
    export PORT=8081
    
    # Start the server
    python3 frontend_server.py
}

show_info() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                    DHI TRANSACTION ANALYTICS DASHBOARD                      ║"
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    echo "║                                                                              ║"
    echo "║  📊 Dashboard URL:    http://localhost:8081                                 ║"
    echo "║  📱 Mobile Friendly:  ✅ Responsive design for all devices                  ║"
    echo "║  🔗 API Docs:         http://localhost:8081/docs                           ║"
    echo "║                                                                              ║"
    echo "║  FEATURES:                                                                   ║"
    echo "║  ✅ Real-time Transaction Analytics                                          ║"
    echo "║  ✅ API Status Monitoring                                                    ║"
    echo "║  ✅ Camera Photo Capture                                                     ║"
    echo "║  ✅ Audio Recording                                                          ║"
    echo "║  ✅ File Upload & Management                                                 ║"
    echo "║  ✅ Progressive Web App (PWA)                                                ║"
    echo "║  ✅ Offline Support                                                          ║"
    echo "║                                                                              ║"
    echo "║  MOBILE FEATURES:                                                            ║"
    echo "║  📱 Touch-optimized interface                                                ║"
    echo "║  📷 Camera switching (front/back)                                           ║"
    echo "║  🎙️ Voice recording                                                          ║"
    echo "║  📤 Drag & drop file upload                                                  ║"
    echo "║  🔔 Push notifications                                                       ║"
    echo "║                                                                              ║"
    echo "║  SERVICES:                                                                   ║"
    echo "║  • Plaid API:     http://localhost:8080                                     ║"
    echo "║  • Neo4j:         bolt://localhost:7687                                     ║"
    echo "║  • Frontend:      http://localhost:8081                                     ║"
    echo "║                                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    print_status "Press Ctrl+C to stop the server"
    echo ""
}

main() {
    case "${1:-start}" in
        start)
            show_info
            check_dependencies
            create_directories
            check_plaid_api
            start_frontend_server
            ;;
        check)
            check_dependencies
            check_plaid_api
            print_success "All checks passed!"
            ;;
        deps)
            check_dependencies
            print_success "Dependencies installed!"
            ;;
        *)
            echo "Usage: $0 [start|check|deps]"
            echo ""
            echo "Commands:"
            echo "  start (default) - Start the frontend server"
            echo "  check          - Check dependencies and services"
            echo "  deps           - Install dependencies only"
            ;;
    esac
}

main "$@"
