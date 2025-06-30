# DHI Core - Testing Guide

## Overview
This guide covers testing strategies and approaches for the DHI Core system, which is a multimodal knowledge management platform with financial transaction analytics capabilities.

## Testing Architecture

### 1. Unit Testing

#### Current Implementation
- **Framework**: pytest (configured in `pyproject.toml`)
- **Current Tests**: Located in `tests/` directory
  - `test_ingestion.py` - Tests file upload and ingestion endpoints

#### Test Categories
```bash
# Run all tests
make test

# Run specific test files
pytest tests/test_ingestion.py -v

# Run with coverage
pytest --cov=dhi_core tests/
```

### 2. Integration Testing

#### API Endpoint Testing
Use FastAPI's TestClient for comprehensive API testing:

```python
from fastapi.testclient import TestClient
from dhi_core.api.app import app

client = TestClient(app)

def test_upload_endpoint():
    # Test file upload functionality
    response = client.post("/upload", 
                          files={"file": ("test.txt", "test content", "text/plain")},
                          data={"media_type": "text"})
    assert response.status_code == 200
```

#### Database Integration Tests
Test database operations across all three databases:

```python
def test_postgres_operations():
    # Test PostgreSQL metadata storage
    pass

def test_weaviate_operations():
    # Test vector database operations
    pass

def test_neo4j_operations():
    # Test graph database operations
    pass
```

### 3. System Testing

#### End-to-End Testing
The system includes several demo scripts for E2E testing:

- `scripts/enhanced_complete_demo.py` - Complete system demonstration
- `scripts/complete_demo.py` - Basic functionality testing
- `scripts/practical_examples.py` - Real-world use case testing

#### Running System Tests
```bash
# Complete system demo
python scripts/enhanced_complete_demo.py

# Basic API testing
python scripts/simple_api_demo.py

# Plaid integration testing
python scripts/plaid_script.py
```

### 4. Performance Testing

#### Load Testing
```bash
# Using ab (Apache Bench)
ab -n 100 -c 10 http://localhost:8000/search?q=test

# Using hey
hey -n 1000 -c 50 http://localhost:8000/search?q=transaction
```

#### Database Performance
```bash
# Neo4j performance monitoring
python scripts/test_graph_analytics.py

# Vector search performance
python scripts/consumption_examples.py
```

## Testing Environment Setup

### 1. Development Environment
```bash
# Setup development environment
make dev-setup
source venv/bin/activate

# Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx
```

### 2. Test Databases
Use Docker containers for isolated testing:

```bash
# Start test databases
docker-compose -f docker-compose.neo4j.yml up -d

# PostgreSQL for testing
docker run -d --name test-postgres \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=test_dhi \
  -p 5433:5432 postgres:15

# Weaviate for testing
docker run -d --name test-weaviate \
  -p 8081:8080 \
  weaviate/weaviate:latest
```

### 3. Environment Variables for Testing
Create `.env.test` file:
```bash
POSTGRES_USER=test
POSTGRES_PASSWORD=test
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=test_dhi

WEAVIATE_URL=http://localhost:8081
NEO4J_URL=bolt://localhost:7688
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpassword

UPLOAD_DIR=./test_data/uploads/
```

## Test Data Management

### 1. Sample Data Creation
```python
# Create test transaction data
python scripts/setup_test_data.py

# Generate sample uploads
mkdir -p test_data/{uploads,audio_uploads,image_uploads}
```

### 2. Mock Data Services
```python
# Mock Plaid API responses
@pytest.fixture
def mock_plaid_client():
    with patch('dhi_core.plaid.client.PlaidClient') as mock:
        # Configure mock responses
        yield mock
```

## Continuous Integration

### GitHub Actions Workflow
Create `.github/workflows/test.yml`:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: pytest --cov=dhi_core tests/
```

## Testing Checklist

### Before Release
- [ ] All unit tests pass
- [ ] API endpoints tested with various inputs
- [ ] Database operations verified
- [ ] File upload/processing tested
- [ ] Authentication/authorization tested
- [ ] Error handling verified
- [ ] Performance benchmarks met
- [ ] Security vulnerabilities scanned

### Manual Testing Areas
- [ ] Frontend dashboard functionality
- [ ] Mobile responsiveness
- [ ] File upload workflows
- [ ] Search and analytics features
- [ ] Plaid integration flows
- [ ] Graph visualizations

## Troubleshooting

### Common Issues
1. **Database Connection Errors**
   - Verify database containers are running
   - Check environment variables
   - Confirm network connectivity

2. **Import Errors**
   - Ensure virtual environment is activated
   - Verify PYTHONPATH includes project root
   - Check for missing dependencies

3. **File Upload Issues**
   - Verify upload directories exist
   - Check file permissions
   - Confirm disk space availability

### Debugging Tools
```bash
# Check service status
make airbyte-status

# View logs
tail -f logs/dhi_core.log

# Test database connections
python scripts/test_database_connections.py
```
