# dhi.core

Core repo for basic functionality to be provided across projects.

## Ingestion API

A simple FastAPI application is included to upload files and record them in a Postgres database.

### Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file in the project root with the `DATABASE_URL` variable pointing to your Postgres instance. Example:
   ```dotenv
   DATABASE_URL=postgresql://user:password@localhost:5432/mydb
   ```
3. Start the server:
   ```bash
   uvicorn ingestion.ingest:app --reload
   ```

Files uploaded via `POST /upload` will be saved to `data/uploads/` and a `Document` record will be created in the `documents` table.
