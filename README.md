# dhi.core

Core repo for basic functionality to be provided across projects.

## Setup


Install the dependencies using the provided `requirements.txt` file:
=======
### Python

Use **Python 3.11** or higher. Create a virtual environment and install the dependencies:


```bash
pip install -r requirements.txt
```

=======

### Environment variables

Copy `.env.example` to `.env` and adjust the values for your environment. The following variables are required.

#### PostgreSQL

```bash
POSTGRES_USER=<username>
POSTGRES_PASSWORD=<password>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=<database>
```

#### Weaviate

```bash
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=
```

#### Neo4j

```bash
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
```

## Running the API

Start the unified API with Uvicorn:

```bash
uvicorn dhi.core.api.app:app --reload
```

## Quick Start (Recommended)

Using the Makefile for automated setup:

```bash
# Complete setup with virtual environment
make setup
source venv/bin/activate

# Start the API server
make dev
```

## Testing the System

### Quick Functionality Test
```bash
# Test core functionalities (API must be running)
python scripts/quick_test.py
```

### Comprehensive Testing
```bash
# Run all tests including database and integrations
python scripts/test_system_comprehensive.py

# Run unit tests
make test
```

### Manual Testing
- **API Documentation**: Visit `http://localhost:8000/docs`
- **Frontend Dashboard**: Visit `http://localhost:8081` (if frontend is running)

## Documentation

- **[Current Status](CURRENT_STATUS.md)** - Overview of implemented features
- **[Testing Guide](TESTING_GUIDE.md)** - Comprehensive testing strategies  
- **[Future Roadmap](FUTURE_ROADMAP.md)** - Development roadmap and goals
- **[Production Guide](PRODUCTION_GUIDE.md)** - Deployment and production setup