#!/usr/bin/env python3
"""
DHI Frontend Backend Server

FastAPI server that serves the frontend dashboard and provides additional
API endpoints for the web application including LLM query processing and
database connection management.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import asyncio
import aiofiles
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Import LLM and database modules
try:
    from dhi_core.llm.query_agent import query_agent, QueryResult as LLMQueryResult
    from dhi_core.database.connection_manager import db_manager, DatabaseType, DatabaseConnection
    LLM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LLM/Database modules not available: {e}")
    LLM_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIStatus(BaseModel):
    service: str
    status: str
    url: str
    response_time: Optional[float] = None
    last_checked: str

class SystemLog(BaseModel):
    timestamp: str
    level: str
    message: str
    source: str

class FileUpload(BaseModel):
    filename: str
    content_type: str
    size: int
    upload_time: str
    file_path: str

class MediaCapture(BaseModel):
    type: str  # 'photo', 'audio', 'video'
    filename: str
    timestamp: str
    file_path: str
    metadata: Dict[str, Any] = {}

# New models for LLM and database features
class NaturalLanguageQuery(BaseModel):
    query: str
    database_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class DatabaseConnectionRequest(BaseModel):
    name: str
    type: str
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl: bool = False

class DirectDatabaseQuery(BaseModel):
    connection_id: str
    query: str
    params: Optional[List[Any]] = None

# Global state
system_logs = []
uploaded_files = []
media_captures = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting DHI Frontend Backend Server")
    
    # Create necessary directories
    os.makedirs("frontend/uploads", exist_ok=True)
    os.makedirs("frontend/media", exist_ok=True)
    os.makedirs("frontend/audio", exist_ok=True)
    
    # Add startup log
    add_system_log("INFO", "Server started successfully", "system")
    
    yield
    
    logger.info("Shutting down DHI Frontend Backend Server")

app = FastAPI(
    title="DHI Frontend Backend",
    description="Backend API for DHI Transaction Analytics Dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

def add_system_log(level: str, message: str, source: str = "api"):
    """Add a log entry to the system logs."""
    log_entry = SystemLog(
        timestamp=datetime.now().isoformat(),
        level=level,
        message=message,
        source=source
    )
    system_logs.append(log_entry)
    
    # Keep only last 100 logs
    if len(system_logs) > 100:
        system_logs.pop(0)

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main dashboard HTML."""
    html_file = frontend_dir / "index.html"
    return FileResponse(html_file)

@app.get("/api/status/all")
async def get_all_status():
    """Get status of all services."""
    statuses = []
    
    # Check Plaid API
    plaid_status = await check_service_status(
        "Plaid API", 
        "http://localhost:8080/health"
    )
    statuses.append(plaid_status)
    
    # Check Neo4j (would need actual endpoint)
    neo4j_status = APIStatus(
        service="Neo4j Database",
        status="unknown",
        url="bolt://localhost:7687",
        last_checked=datetime.now().isoformat()
    )
    statuses.append(neo4j_status)
    
    add_system_log("INFO", f"Status check completed for {len(statuses)} services", "status")
    
    return {"statuses": statuses}

async def check_service_status(service_name: str, url: str) -> APIStatus:
    """Check the status of a service."""
    start_time = datetime.now()
    
    try:
        response = requests.get(url, timeout=5)
        response_time = (datetime.now() - start_time).total_seconds()
        
        if response.status_code == 200:
            status = "online"
        else:
            status = "error"
            
    except requests.exceptions.RequestException as e:
        status = "offline"
        response_time = None
        add_system_log("WARNING", f"{service_name} is offline: {str(e)}", "status")
    
    return APIStatus(
        service=service_name,
        status=status,
        url=url,
        response_time=response_time,
        last_checked=datetime.now().isoformat()
    )

@app.get("/api/logs")
async def get_system_logs():
    """Get system logs."""
    return {"logs": system_logs}

@app.delete("/api/logs")
async def clear_system_logs():
    """Clear system logs."""
    global system_logs
    system_logs = []
    add_system_log("INFO", "System logs cleared", "api")
    return {"message": "Logs cleared successfully"}

@app.get("/api/plaid/proxy/{endpoint:path}")
async def plaid_proxy(endpoint: str, request: Request):
    """Proxy requests to Plaid API service."""
    plaid_url = f"http://localhost:8080/{endpoint}"
    
    try:
        # Forward query parameters
        params = dict(request.query_params)
        response = requests.get(plaid_url, params=params, timeout=10)
        
        add_system_log("INFO", f"Proxied request to Plaid API: /{endpoint}", "proxy")
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        add_system_log("ERROR", f"Plaid API proxy error: {str(e)}", "proxy")
        raise HTTPException(status_code=503, detail=f"Plaid API unavailable: {str(e)}")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file."""
    try:
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = f"frontend/uploads/{filename}"
        
        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        
        # Create upload record
        upload_record = FileUpload(
            filename=file.filename,
            content_type=file.content_type,
            size=len(content),
            upload_time=datetime.now().isoformat(),
            file_path=file_path
        )
        
        uploaded_files.append(upload_record)
        
        add_system_log("INFO", f"File uploaded: {file.filename} ({len(content)} bytes)", "upload")
        
        return {
            "message": "File uploaded successfully",
            "filename": filename,
            "size": len(content),
            "content_type": file.content_type
        }
        
    except Exception as e:
        add_system_log("ERROR", f"File upload failed: {str(e)}", "upload")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/uploads")
async def get_uploaded_files():
    """Get list of uploaded files."""
    return {"files": uploaded_files}

@app.post("/api/media/photo")
async def save_photo(
    photo_data: str = Form(...),
    filename: str = Form(...)
):
    """Save a captured photo."""
    try:
        # Decode base64 image data
        import base64
        
        # Remove data:image/jpeg;base64, prefix if present
        if photo_data.startswith('data:'):
            photo_data = photo_data.split(',')[1]
        
        image_data = base64.b64decode(photo_data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_filename = f"photo_{timestamp}.jpg"
        file_path = f"frontend/media/{photo_filename}"
        
        # Save image
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(image_data)
        
        # Create media record
        media_record = MediaCapture(
            type="photo",
            filename=photo_filename,
            timestamp=datetime.now().isoformat(),
            file_path=file_path,
            metadata={"original_filename": filename}
        )
        
        media_captures.append(media_record)
        
        add_system_log("INFO", f"Photo captured: {photo_filename}", "media")
        
        return {
            "message": "Photo saved successfully",
            "filename": photo_filename,
            "path": f"/api/media/{photo_filename}"
        }
        
    except Exception as e:
        add_system_log("ERROR", f"Photo save failed: {str(e)}", "media")
        raise HTTPException(status_code=500, detail=f"Failed to save photo: {str(e)}")

@app.post("/api/media/audio")
async def save_audio(
    audio: UploadFile = File(...),
    name: str = Form(...)
):
    """Save an audio recording."""
    try:
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f"audio_{timestamp}.webm"
        file_path = f"frontend/audio/{audio_filename}"
        
        # Save audio file
        async with aiofiles.open(file_path, "wb") as f:
            content = await audio.read()
            await f.write(content)
        
        # Create media record
        media_record = MediaCapture(
            type="audio",
            filename=audio_filename,
            timestamp=datetime.now().isoformat(),
            file_path=file_path,
            metadata={
                "original_name": name,
                "size": len(content),
                "content_type": audio.content_type
            }
        )
        
        media_captures.append(media_record)
        
        add_system_log("INFO", f"Audio recorded: {audio_filename}", "media")
        
        return {
            "message": "Audio saved successfully",
            "filename": audio_filename,
            "path": f"/api/media/{audio_filename}"
        }
        
    except Exception as e:
        add_system_log("ERROR", f"Audio save failed: {str(e)}", "media")
        raise HTTPException(status_code=500, detail=f"Failed to save audio: {str(e)}")

@app.get("/api/media")
async def get_media_captures():
    """Get list of media captures."""
    return {"media": media_captures}

@app.get("/api/media/{filename}")
async def get_media_file(filename: str):
    """Serve a media file."""
    # Check in both media and audio directories
    for directory in ["frontend/media", "frontend/audio"]:
        file_path = Path(directory) / filename
        if file_path.exists():
            return FileResponse(file_path)
    
    raise HTTPException(status_code=404, detail="Media file not found")

@app.get("/api/analytics/dashboard")
async def get_dashboard_analytics():
    """Get dashboard analytics data."""
    try:
        # Fetch data from Plaid API
        accounts_response = requests.get("http://localhost:8080/accounts", timeout=5)
        transactions_response = requests.get("http://localhost:8080/transactions", timeout=5)
        
        accounts_data = accounts_response.json()
        transactions_data = transactions_response.json()
        
        # Process analytics
        transactions = transactions_data.get("data", [])
        
        # Calculate statistics
        total_transactions = len(transactions)
        total_amount = sum(float(t.get("amount", 0)) for t in transactions)
        unique_merchants = len(set(t.get("merchant_name") for t in transactions if t.get("merchant_name")))
        
        # Simple anomaly detection
        amounts = [float(t.get("amount", 0)) for t in transactions]
        if amounts:
            avg_amount = sum(amounts) / len(amounts)
            anomalies = len([a for a in amounts if a > avg_amount * 2])
        else:
            anomalies = 0
        
        # Category breakdown
        categories = {}
        for t in transactions:
            category = t.get("category", "Other")
            categories[category] = categories.get(category, 0) + float(t.get("amount", 0))
        
        # Monthly trends
        monthly_data = {}
        for t in transactions:
            month = t.get("date", "")[:7]  # YYYY-MM
            monthly_data[month] = monthly_data.get(month, 0) + float(t.get("amount", 0))
        
        add_system_log("INFO", "Dashboard analytics generated", "analytics")
        
        return {
            "statistics": {
                "total_transactions": total_transactions,
                "total_amount": total_amount,
                "unique_merchants": unique_merchants,
                "anomalies": anomalies
            },
            "categories": categories,
            "monthly_trends": monthly_data,
            "last_updated": datetime.now().isoformat()
        }
        
    except requests.exceptions.RequestException as e:
        add_system_log("ERROR", f"Analytics generation failed: {str(e)}", "analytics")
        raise HTTPException(status_code=503, detail="Unable to fetch transaction data")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "frontend": "online",
            "api": "online"
        }
    }

@app.post("/api/settings")
async def save_settings(settings: Dict[str, Any]):
    """Save application settings."""
    try:
        settings_file = "frontend/settings.json"
        
        async with aiofiles.open(settings_file, "w") as f:
            await f.write(json.dumps(settings, indent=2))
        
        add_system_log("INFO", "Settings saved", "settings")
        
        return {"message": "Settings saved successfully"}
        
    except Exception as e:
        add_system_log("ERROR", f"Settings save failed: {str(e)}", "settings")
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@app.get("/api/settings")
async def get_settings():
    """Get application settings."""
    try:
        settings_file = "frontend/settings.json"
        
        if os.path.exists(settings_file):
            async with aiofiles.open(settings_file, "r") as f:
                content = await f.read()
                settings = json.loads(content)
        else:
            # Default settings
            settings = {
                "plaid_api_url": "http://localhost:8080",
                "neo4j_url": "bolt://localhost:7687",
                "refresh_interval": 30,
                "theme": "light",
                "enable_notifications": True,
                "auto_refresh": True
            }
        
        return {"settings": settings}
        
    except Exception as e:
        add_system_log("ERROR", f"Settings load failed: {str(e)}", "settings")
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {str(e)}")

@app.websocket("/ws/logs")
async def websocket_logs(websocket):
    """WebSocket endpoint for real-time logs."""
    await websocket.accept()
    
    try:
        # Send existing logs
        await websocket.send_json({"type": "initial", "logs": system_logs})
        
        # Keep connection alive and send new logs
        last_log_count = len(system_logs)
        
        while True:
            await asyncio.sleep(1)
            
            current_log_count = len(system_logs)
            if current_log_count > last_log_count:
                # Send new logs
                new_logs = system_logs[last_log_count:]
                await websocket.send_json({"type": "update", "logs": new_logs})
                last_log_count = current_log_count
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# New endpoints for LLM and database features

@app.post("/api/llm/query")
async def llm_query(query: NaturalLanguageQuery):
    """Process a natural language query using the LLM."""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM service not available")
    
    try:
        # Execute query using LLM
        result = query_agent.run(query.query, context=query.context)
        
        # Log the query
        add_system_log("INFO", f"LLM query executed: {query.query}", "llm")
        
        return {"result": result}
        
    except Exception as e:
        add_system_log("ERROR", f"LLM query failed: {str(e)}", "llm")
        raise HTTPException(status_code=500, detail=f"LLM query failed: {str(e)}")

@app.post("/api/database/connect")
async def connect_database(connection: DatabaseConnectionRequest):
    """Establish a connection to a database."""
    try:
        # Create database connection
        db_connection = DatabaseConnection(
            name=connection.name,
            type=DatabaseType[connection.type.upper()],
            host=connection.host,
            port=connection.port,
            database=connection.database,
            username=connection.username,
            password=connection.password,
            ssl=connection.ssl
        )
        
        # Test the connection
        await db_manager.test_connection(db_connection)
        
        # Log the connection
        add_system_log("INFO", f"Database connected: {connection.name}", "database")
        
        return {"message": "Database connected successfully"}
        
    except Exception as e:
        add_system_log("ERROR", f"Database connection failed: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.post("/api/database/query")
async def database_query(query: DirectDatabaseQuery):
    """Execute a direct query on the connected database."""
    try:
        # Get the database connection
        db_connection = db_manager.get_connection(query.connection_id)
        if not db_connection:
            raise HTTPException(status_code=404, detail="Database connection not found")
        
        # Execute the query
        result = await db_manager.execute_query(db_connection, query.query, query.params)
        
        # Log the query
        add_system_log("INFO", f"Database query executed: {query.query}", "database")
        
        return {"result": result}
        
    except Exception as e:
        add_system_log("ERROR", f"Database query failed: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

@app.post("/api/llm/query")
async def llm_query(query: NaturalLanguageQuery):
    """Process a natural language query using the LLM."""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="LLM service not available")
    
    try:
        # Execute query using LLM
        result = await query_agent.process_natural_language_query(
            query.query, 
            context=query.context
        )
        
        # Log the query
        add_system_log("INFO", f"LLM query executed: {query.query[:50]}...", "llm")
        
        return {"result": result.__dict__}
        
    except Exception as e:
        add_system_log("ERROR", f"LLM query failed: {str(e)}", "llm")
        raise HTTPException(status_code=500, detail=f"LLM query failed: {str(e)}")

@app.get("/api/database/connections")
async def get_database_connections():
    """Get all database connections."""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        connections = db_manager.get_connections()
        return {"connections": [conn.__dict__ for conn in connections]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connections: {str(e)}")

@app.post("/api/database/connect")
async def connect_database(connection: DatabaseConnectionRequest):
    """Add and connect to a database."""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        # Generate connection ID
        connection_id = f"{connection.type}_{connection.name.lower().replace(' ', '_')}"
        
        # Add database connection
        success = db_manager.add_connection(
            connection_id=connection_id,
            name=connection.name,
            db_type=DatabaseType[connection.type.upper()],
            host=connection.host,
            port=connection.port,
            database=connection.database,
            username=connection.username,
            password=connection.password,
            ssl=connection.ssl
        )
        
        if success:
            # Try to connect
            await db_manager.connect(connection_id)
            
            # Log the connection
            add_system_log("INFO", f"Database connected: {connection.name}", "database")
            
            return {"message": "Database connected successfully", "connection_id": connection_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to add database connection")
        
    except Exception as e:
        add_system_log("ERROR", f"Database connection failed: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.post("/api/database/test")
async def test_database_connection(connection: DatabaseConnectionRequest):
    """Test a database connection without saving it."""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        # Create temporary connection
        temp_id = f"temp_{connection.type}_{datetime.now().timestamp()}"
        
        # Add temporary connection
        db_manager.add_connection(
            connection_id=temp_id,
            name=connection.name,
            db_type=DatabaseType[connection.type.upper()],
            host=connection.host,
            port=connection.port,
            database=connection.database,
            username=connection.username,
            password=connection.password,
            ssl=connection.ssl
        )
        
        # Test connection
        result = await db_manager.test_connection(temp_id)
        
        # Remove temporary connection
        db_manager.remove_connection(temp_id)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "details": {"error": str(e)}
        }

@app.post("/api/database/query")
async def database_query(query: DirectDatabaseQuery):
    """Execute a direct query on the connected database."""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        # Execute the query
        result = await db_manager.execute_query(
            query.connection_id, 
            query.query, 
            query.params
        )
        
        # Log the query
        add_system_log("INFO", f"Database query executed on {query.connection_id}", "database")
        
        return {"result": result.__dict__}
        
    except Exception as e:
        add_system_log("ERROR", f"Database query failed: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

@app.get("/api/database/test/{connection_id}")
async def test_existing_connection(connection_id: str):
    """Test an existing database connection."""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        result = await db_manager.test_connection(connection_id)
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "details": {"error": str(e)}
        }

@app.post("/api/database/connect/{connection_id}")
async def connect_existing_database(connection_id: str):
    """Connect to an existing database configuration."""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        success = await db_manager.connect(connection_id)
        
        if success:
            add_system_log("INFO", f"Database connected: {connection_id}", "database")
            return {"message": "Database connected successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to connect to database")
        
    except Exception as e:
        add_system_log("ERROR", f"Database connection failed: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.delete("/api/database/connections/{connection_id}")
async def remove_database_connection(connection_id: str):
    """Remove a database connection."""
    if not LLM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        success = db_manager.remove_connection(connection_id)
        
        if success:
            add_system_log("INFO", f"Database connection removed: {connection_id}", "database")
            return {"message": "Database connection removed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Database connection not found")
        
    except Exception as e:
        add_system_log("ERROR", f"Failed to remove database connection: {str(e)}", "database")
        raise HTTPException(status_code=500, detail=f"Failed to remove connection: {str(e)}")

if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8081))
    
    print(f"""
🚀 DHI Frontend Backend Server Starting...

📊 Dashboard URL: http://localhost:{port}
🔗 API Docs: http://localhost:{port}/docs
📱 Mobile-friendly responsive design included

Features:
✅ Transaction Analytics Dashboard
✅ Real-time API Status Monitoring  
✅ Camera Capture (Photo/Video)
✅ Audio Recording
✅ File Upload & Management
✅ System Logs & Monitoring
✅ Responsive Mobile Design
✅ LLM Natural Language Queries
✅ Multi-Database Management
✅ AI-Powered Data Insights

Services Integration:
- Plaid API: http://localhost:8080
- Neo4j DB: bolt://localhost:7687
- Frontend: http://localhost:{port}
""")
    
    uvicorn.run(
        "frontend_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
