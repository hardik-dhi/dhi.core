#!/usr/bin/env python3
"""
Airbyte Setup Script for Plaid Integration

This script automates the setup of Airbyte with Plaid data sync to PostgreSQL.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

class AirbyteSetup:
    def __init__(self, airbyte_url="http://localhost:8001"):
        self.airbyte_url = airbyte_url
        self.api_url = f"{airbyte_url}/api/v1"
        self.workspace_id = None
        
    def wait_for_airbyte(self, timeout=300):
        """Wait for Airbyte to be ready."""
        print("🔄 Waiting for Airbyte to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.api_url}/health")
                if response.status_code == 200:
                    print("✅ Airbyte is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(5)
            print("⏳ Still waiting for Airbyte...")
        
        print("❌ Timeout waiting for Airbyte to be ready")
        return False
    
    def get_workspace(self):
        """Get the default workspace."""
        try:
            response = requests.post(f"{self.api_url}/workspaces/list")
            if response.status_code == 200:
                workspaces = response.json()["workspaces"]
                if workspaces:
                    self.workspace_id = workspaces[0]["workspaceId"]
                    print(f"✅ Using workspace: {self.workspace_id}")
                    return True
            
            print("❌ No workspaces found")
            return False
        except Exception as e:
            print(f"❌ Error getting workspace: {e}")
            return False
    
    def create_source_definition(self):
        """Create HTTP source definition for Plaid API."""
        source_def_data = {
            "name": "Custom HTTP Source",
            "dockerRepository": "airbyte/source-http-request",
            "dockerImageTag": "0.2.0",
            "documentationUrl": "https://docs.airbyte.com/integrations/sources/http-request"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/source_definitions/create_custom",
                json={
                    "sourceDefinition": source_def_data,
                    "workspaceId": self.workspace_id
                }
            )
            
            if response.status_code == 200:
                source_def_id = response.json()["sourceDefinitionId"]
                print(f"✅ Created custom HTTP source definition: {source_def_id}")
                return source_def_id
            else:
                print(f"❌ Failed to create source definition: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating source definition: {e}")
            return None
    
    def create_plaid_source(self):
        """Create Plaid source connection."""
        source_config = {
            "name": "Plaid Transactions Source",
            "sourceDefinitionId": "778daa7c-feaf-4db6-96f3-70fd645acc77",  # HTTP source
            "workspaceId": self.workspace_id,
            "connectionConfiguration": {
                "name": "Plaid API",
                "base_url": "http://plaid-api:8080",
                "streams": [
                    {
                        "name": "accounts",
                        "url_path": "/accounts",
                        "http_method": "GET",
                        "primary_key": ["account_id"]
                    },
                    {
                        "name": "transactions", 
                        "url_path": "/transactions",
                        "http_method": "GET",
                        "primary_key": ["transaction_id"],
                        "cursor_field": ["updated_at"]
                    }
                ]
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/sources/create",
                json=source_config
            )
            
            if response.status_code == 200:
                source_id = response.json()["sourceId"]
                print(f"✅ Created Plaid source: {source_id}")
                return source_id
            else:
                print(f"❌ Failed to create Plaid source: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating Plaid source: {e}")
            return None
    
    def create_postgres_destination(self):
        """Create PostgreSQL destination connection."""
        dest_config = {
            "name": "PostgreSQL Destination",
            "destinationDefinitionId": "25c5221d-dce2-4163-ade9-739ef790f503",  # Postgres
            "workspaceId": self.workspace_id,
            "connectionConfiguration": {
                "host": "host.docker.internal",
                "port": 5432,
                "database": "postgres",
                "schema": "airbyte_plaid",
                "username": "postgres",
                "password": "postgres",
                "ssl": False
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/destinations/create",
                json=dest_config
            )
            
            if response.status_code == 200:
                dest_id = response.json()["destinationId"]
                print(f"✅ Created PostgreSQL destination: {dest_id}")
                return dest_id
            else:
                print(f"❌ Failed to create PostgreSQL destination: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating PostgreSQL destination: {e}")
            return None
    
    def create_connection(self, source_id, dest_id):
        """Create connection between source and destination."""
        connection_config = {
            "name": "Plaid to PostgreSQL",
            "sourceId": source_id,
            "destinationId": dest_id,
            "syncCatalog": {
                "streams": [
                    {
                        "stream": {
                            "name": "accounts",
                            "supportedSyncModes": ["full_refresh"]
                        },
                        "config": {
                            "syncMode": "full_refresh",
                            "destinationSyncMode": "overwrite"
                        }
                    },
                    {
                        "stream": {
                            "name": "transactions",
                            "supportedSyncModes": ["incremental"]
                        },
                        "config": {
                            "syncMode": "incremental",
                            "destinationSyncMode": "append",
                            "cursorField": ["updated_at"]
                        }
                    }
                ]
            },
            "schedule": {
                "scheduleType": "cron",
                "cronExpression": "0 */6 * * *"  # Every 6 hours
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/connections/create",
                json=connection_config
            )
            
            if response.status_code == 200:
                connection_id = response.json()["connectionId"]
                print(f"✅ Created connection: {connection_id}")
                return connection_id
            else:
                print(f"❌ Failed to create connection: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating connection: {e}")
            return None
    
    def trigger_sync(self, connection_id):
        """Trigger a manual sync."""
        try:
            response = requests.post(
                f"{self.api_url}/connections/sync",
                json={"connectionId": connection_id}
            )
            
            if response.status_code == 200:
                job_id = response.json()["job"]["id"]
                print(f"✅ Triggered sync job: {job_id}")
                return job_id
            else:
                print(f"❌ Failed to trigger sync: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error triggering sync: {e}")
            return None
    
    def setup_complete_pipeline(self):
        """Set up the complete Airbyte pipeline."""
        print("🚀 Setting up Airbyte Plaid integration pipeline...")
        
        # Wait for Airbyte to be ready
        if not self.wait_for_airbyte():
            return False
        
        # Get workspace
        if not self.get_workspace():
            return False
        
        # Create source
        source_id = self.create_plaid_source()
        if not source_id:
            return False
        
        # Create destination
        dest_id = self.create_postgres_destination()
        if not dest_id:
            return False
        
        # Create connection
        connection_id = self.create_connection(source_id, dest_id)
        if not connection_id:
            return False
        
        # Trigger initial sync
        job_id = self.trigger_sync(connection_id)
        if job_id:
            print(f"✅ Initial sync started: {job_id}")
        
        print("🎉 Airbyte Plaid integration setup complete!")
        print(f"📱 Airbyte UI: http://localhost:8000")
        print(f"🔗 Connection ID: {connection_id}")
        print(f"📊 Data will be synced to schema: airbyte_plaid")
        
        return True

def main():
    """Main setup function."""
    setup = AirbyteSetup()
    
    print("🏦 DHI Core - Airbyte Plaid Integration Setup")
    print("=" * 50)
    
    if setup.setup_complete_pipeline():
        print("\n✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Visit http://localhost:8000 to access Airbyte UI")
        print("2. Check the connection status and sync history")
        print("3. Query your PostgreSQL database to see synced data")
        print("4. The sync will run automatically every 6 hours")
    else:
        print("\n❌ Setup failed. Please check the logs and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()