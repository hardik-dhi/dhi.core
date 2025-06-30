#!/usr/bin/env python3
"""
Database Connection Manager

Unified interface for managing multiple database connections including
PostgreSQL, Neo4j, SQLite, and other data sources.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio
from enum import Enum

import asyncpg
import sqlite3
import aiosqlite
from neo4j import GraphDatabase
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd

logger = logging.getLogger(__name__)

class DatabaseType(Enum):
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    NEO4J = "neo4j"
    REDIS = "redis"
    MYSQL = "mysql"
    MONGODB = "mongodb"

@dataclass
class DatabaseConnection:
    id: str
    name: str
    type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl: bool = False
    connection_string: Optional[str] = None
    is_active: bool = False
    last_connected: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class QueryResult:
    success: bool
    data: Any
    columns: List[str]
    row_count: int
    execution_time: float
    query: str
    database_id: str
    error_message: Optional[str] = None

class DatabaseManager:
    """
    Central manager for all database connections and operations.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.connections: Dict[str, DatabaseConnection] = {}
        self.active_connections: Dict[str, Any] = {}
        self.config_path = config_path or "frontend/settings.json"
        
        # Load existing connections
        self._load_connections()
        
        # Default connections
        self._setup_default_connections()
    
    def _load_connections(self):
        """Load database connections from configuration file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    
                db_configs = config.get('database_connections', [])
                for db_config in db_configs:
                    conn = DatabaseConnection(**db_config)
                    self.connections[conn.id] = conn
                    
                logger.info(f"Loaded {len(self.connections)} database connections")
        except Exception as e:
            logger.error(f"Error loading database connections: {e}")
    
    def _save_connections(self):
        """Save database connections to configuration file."""
        try:
            # Load existing config or create new
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            
            # Update database connections
            config['database_connections'] = [
                asdict(conn) for conn in self.connections.values()
            ]
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2, default=str)
                
            logger.info("Database connections saved to configuration")
        except Exception as e:
            logger.error(f"Error saving database connections: {e}")
    
    def _setup_default_connections(self):
        """Setup default database connections."""
        
        # SQLite default connection (for demo/development)
        if "sqlite_default" not in self.connections:
            self.add_connection(
                connection_id="sqlite_default",
                name="Local SQLite Database",
                db_type=DatabaseType.SQLITE,
                host="localhost",
                port=0,
                database="data/transactions.db",
                username="",
                password=""
            )
        
        # Neo4j default connection
        if "neo4j_default" not in self.connections:
            self.add_connection(
                connection_id="neo4j_default", 
                name="Neo4j Graph Database",
                db_type=DatabaseType.NEO4J,
                host="localhost",
                port=7687,
                database="neo4j",
                username="neo4j",
                password="password"
            )
        
        # PostgreSQL connection (if configured)
        pg_host = os.getenv('POSTGRES_HOST')
        if pg_host and "postgres_default" not in self.connections:
            self.add_connection(
                connection_id="postgres_default",
                name="PostgreSQL Database", 
                db_type=DatabaseType.POSTGRESQL,
                host=pg_host,
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database=os.getenv('POSTGRES_DB', 'dhi_analytics'),
                username=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'password')
            )
    
    def add_connection(self, connection_id: str, name: str, db_type: DatabaseType,
                      host: str, port: int, database: str, username: str, 
                      password: str, ssl: bool = False, **kwargs) -> bool:
        """Add a new database connection."""
        try:
            connection = DatabaseConnection(
                id=connection_id,
                name=name,
                type=db_type,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                ssl=ssl,
                metadata=kwargs
            )
            
            self.connections[connection_id] = connection
            self._save_connections()
            
            logger.info(f"Added database connection: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding database connection: {e}")
            return False
    
    def remove_connection(self, connection_id: str) -> bool:
        """Remove a database connection."""
        try:
            if connection_id in self.connections:
                # Close active connection if exists
                if connection_id in self.active_connections:
                    self.disconnect(connection_id)
                
                del self.connections[connection_id]
                self._save_connections()
                
                logger.info(f"Removed database connection: {connection_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing database connection: {e}")
            return False
    
    def get_connections(self) -> List[DatabaseConnection]:
        """Get all database connections."""
        return list(self.connections.values())
    
    def get_connection(self, connection_id: str) -> Optional[DatabaseConnection]:
        """Get a specific database connection."""
        return self.connections.get(connection_id)
    
    async def connect(self, connection_id: str) -> bool:
        """Establish connection to a database."""
        try:
            if connection_id not in self.connections:
                logger.error(f"Connection {connection_id} not found")
                return False
            
            conn_config = self.connections[connection_id]
            
            if conn_config.type == DatabaseType.POSTGRESQL:
                connection = await self._connect_postgresql(conn_config)
            elif conn_config.type == DatabaseType.SQLITE:
                connection = await self._connect_sqlite(conn_config)
            elif conn_config.type == DatabaseType.NEO4J:
                connection = await self._connect_neo4j(conn_config)
            elif conn_config.type == DatabaseType.REDIS:
                connection = await self._connect_redis(conn_config)
            else:
                logger.error(f"Unsupported database type: {conn_config.type}")
                return False
            
            if connection:
                self.active_connections[connection_id] = connection
                self.connections[connection_id].is_active = True
                self.connections[connection_id].last_connected = datetime.now()
                logger.info(f"Connected to database: {conn_config.name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to database {connection_id}: {e}")
            return False
    
    async def _connect_postgresql(self, config: DatabaseConnection):
        """Connect to PostgreSQL database."""
        try:
            connection_string = f"postgresql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
            if config.ssl:
                connection_string += "?sslmode=require"
            
            connection = await asyncpg.connect(connection_string)
            return connection
        except Exception as e:
            logger.error(f"PostgreSQL connection error: {e}")
            return None
    
    async def _connect_sqlite(self, config: DatabaseConnection):
        """Connect to SQLite database."""
        try:
            # Ensure directory exists
            db_path = config.database
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            connection = await aiosqlite.connect(db_path)
            return connection
        except Exception as e:
            logger.error(f"SQLite connection error: {e}")
            return None
    
    async def _connect_neo4j(self, config: DatabaseConnection):
        """Connect to Neo4j database."""
        try:
            uri = f"bolt://{config.host}:{config.port}"
            driver = GraphDatabase.driver(uri, auth=(config.username, config.password))
            
            # Test connection
            with driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
            
            return driver
        except Exception as e:
            logger.error(f"Neo4j connection error: {e}")
            return None
    
    async def _connect_redis(self, config: DatabaseConnection):
        """Connect to Redis database."""
        try:
            connection = redis.Redis(
                host=config.host,
                port=config.port,
                password=config.password,
                decode_responses=True
            )
            
            # Test connection
            connection.ping()
            return connection
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            return None
    
    def disconnect(self, connection_id: str):
        """Disconnect from a database."""
        try:
            if connection_id in self.active_connections:
                connection = self.active_connections[connection_id]
                config = self.connections[connection_id]
                
                if config.type == DatabaseType.POSTGRESQL:
                    asyncio.create_task(connection.close())
                elif config.type == DatabaseType.SQLITE:
                    asyncio.create_task(connection.close())
                elif config.type == DatabaseType.NEO4J:
                    connection.close()
                elif config.type == DatabaseType.REDIS:
                    connection.close()
                
                del self.active_connections[connection_id]
                self.connections[connection_id].is_active = False
                
                logger.info(f"Disconnected from database: {connection_id}")
        except Exception as e:
            logger.error(f"Error disconnecting from database {connection_id}: {e}")
    
    async def execute_query(self, connection_id: str, query: str, params: List[Any] = None) -> QueryResult:
        """Execute a query on the specified database."""
        start_time = datetime.now()
        
        try:
            if connection_id not in self.active_connections:
                await self.connect(connection_id)
            
            if connection_id not in self.active_connections:
                return QueryResult(
                    success=False,
                    data=None,
                    columns=[],
                    row_count=0,
                    execution_time=0.0,
                    query=query,
                    database_id=connection_id,
                    error_message="Database connection not available"
                )
            
            connection = self.active_connections[connection_id]
            config = self.connections[connection_id]
            
            if config.type == DatabaseType.POSTGRESQL:
                result = await self._execute_postgresql_query(connection, query, params)
            elif config.type == DatabaseType.SQLITE:
                result = await self._execute_sqlite_query(connection, query, params)
            elif config.type == DatabaseType.NEO4J:
                result = await self._execute_neo4j_query(connection, query, params)
            else:
                raise Exception(f"Query execution not implemented for {config.type}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                success=True,
                data=result['data'],
                columns=result['columns'],
                row_count=len(result['data']) if result['data'] else 0,
                execution_time=execution_time,
                query=query,
                database_id=connection_id
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Query execution error: {e}")
            
            return QueryResult(
                success=False,
                data=None,
                columns=[],
                row_count=0,
                execution_time=execution_time,
                query=query,
                database_id=connection_id,
                error_message=str(e)
            )
    
    async def _execute_postgresql_query(self, connection, query: str, params: List[Any] = None):
        """Execute PostgreSQL query."""
        try:
            if params:
                results = await connection.fetch(query, *params)
            else:
                results = await connection.fetch(query)
            
            if results:
                columns = list(results[0].keys())
                data = [dict(row) for row in results]
            else:
                columns = []
                data = []
            
            return {'data': data, 'columns': columns}
        except Exception as e:
            logger.error(f"PostgreSQL query error: {e}")
            raise
    
    async def _execute_sqlite_query(self, connection, query: str, params: List[Any] = None):
        """Execute SQLite query."""
        try:
            if params:
                cursor = await connection.execute(query, params)
            else:
                cursor = await connection.execute(query)
            
            results = await cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            
            # Convert to list of dictionaries
            data = []
            for row in results:
                data.append(dict(zip(columns, row)))
            
            return {'data': data, 'columns': columns}
        except Exception as e:
            logger.error(f"SQLite query error: {e}")
            raise
    
    async def _execute_neo4j_query(self, driver, query: str, params: List[Any] = None):
        """Execute Neo4j Cypher query."""
        try:
            with driver.session() as session:
                if params:
                    result = session.run(query, params)
                else:
                    result = session.run(query)
                
                records = []
                columns = []
                
                for record in result:
                    if not columns:
                        columns = list(record.keys())
                    records.append(dict(record))
                
                return {'data': records, 'columns': columns}
        except Exception as e:
            logger.error(f"Neo4j query error: {e}")
            raise
    
    async def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """Test database connection and return status."""
        try:
            config = self.connections.get(connection_id)
            if not config:
                return {
                    'success': False,
                    'message': 'Connection not found',
                    'details': {}
                }
            
            # Try to connect
            success = await self.connect(connection_id)
            
            if success:
                # Try a simple query
                if config.type == DatabaseType.POSTGRESQL:
                    test_query = "SELECT version()"
                elif config.type == DatabaseType.SQLITE:
                    test_query = "SELECT sqlite_version()"
                elif config.type == DatabaseType.NEO4J:
                    test_query = "RETURN 'connection_test' as test"
                else:
                    test_query = None
                
                if test_query:
                    result = await self.execute_query(connection_id, test_query)
                    
                    return {
                        'success': result.success,
                        'message': 'Connection successful' if result.success else 'Query test failed',
                        'details': {
                            'execution_time': result.execution_time,
                            'database_type': config.type.value,
                            'query_result': result.data[:1] if result.data else None
                        }
                    }
                else:
                    return {
                        'success': True,
                        'message': 'Connection successful',
                        'details': {'database_type': config.type.value}
                    }
            else:
                return {
                    'success': False,
                    'message': 'Connection failed',
                    'details': {}
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection test error: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def get_database_schema(self, connection_id: str) -> Dict[str, Any]:
        """Get database schema information."""
        config = self.connections.get(connection_id)
        if not config:
            return {}
        
        # Return cached schema info or query database
        if config.type == DatabaseType.SQLITE:
            return {
                'tables': ['transactions', 'accounts', 'categories'],
                'views': [],
                'type': 'relational'
            }
        elif config.type == DatabaseType.NEO4J:
            return {
                'nodes': ['Transaction', 'Account', 'Merchant', 'Category'],
                'relationships': ['BELONGS_TO', 'PAID_TO', 'CATEGORIZED_AS'],
                'type': 'graph'
            }
        else:
            return {'type': 'unknown'}
    
    def close_all_connections(self):
        """Close all active database connections."""
        for connection_id in list(self.active_connections.keys()):
            self.disconnect(connection_id)

# Singleton instance
db_manager = DatabaseManager()
