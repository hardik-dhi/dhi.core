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

