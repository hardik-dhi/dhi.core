#!/usr/bin/env python3
"""
Frontend Demo Script

This script demonstrates the frontend features and tests the backend API.
"""

import os
import sys
import time
import json
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

class FrontendDemo:
    """Demo class for testing frontend functionality."""
    
    def __init__(self):
        self.frontend_url = "http://localhost:8081"
        self.plaid_url = "http://localhost:8080"
    
    def check_services(self):
        """Check if services are running."""
        print("🔍 Checking Services Status...")
        print("-" * 40)
        
        # Check frontend
        try:
            response = requests.get(f"{self.frontend_url}/api/health", timeout=5)
            if response.status_code == 200:
                print("✅ Frontend Server: ONLINE")
                frontend_healthy = True
            else:
                print("❌ Frontend Server: ERROR")
                frontend_healthy = False
        except requests.exceptions.RequestException:
            print("❌ Frontend Server: OFFLINE")
            frontend_healthy = False
        
        # Check Plaid API
        try:
            response = requests.get(f"{self.plaid_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Plaid API Service: ONLINE")
                plaid_healthy = True
            else:
                print("❌ Plaid API Service: ERROR")
                plaid_healthy = False
        except requests.exceptions.RequestException:
            print("❌ Plaid API Service: OFFLINE")
            plaid_healthy = False
        
        print()
        return frontend_healthy, plaid_healthy
    
    def test_api_endpoints(self):
        """Test frontend API endpoints."""
        print("🧪 Testing API Endpoints...")
        print("-" * 40)
        
        endpoints = [
            ("/api/health", "Health Check"),
            ("/api/status/all", "Status Check"),
            ("/api/logs", "System Logs"),
            ("/api/settings", "Settings"),
            ("/api/analytics/dashboard", "Dashboard Analytics")
        ]
        
        for endpoint, description in endpoints:
            try:
                response = requests.get(f"{self.frontend_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    print(f"✅ {description}: OK")
                else:
                    print(f"❌ {description}: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"❌ {description}: ERROR - {str(e)}")
        
        print()
    
    def test_plaid_proxy(self):
        """Test Plaid API proxy functionality."""
        print("🔗 Testing Plaid API Proxy...")
        print("-" * 40)
        
        proxy_endpoints = [
            ("accounts", "Accounts Data"),
            ("transactions", "Transactions Data"),
            ("health", "Health Check")
        ]
        
        for endpoint, description in proxy_endpoints:
            try:
                response = requests.get(f"{self.frontend_url}/api/plaid/proxy/{endpoint}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if endpoint == "accounts" and "data" in data:
                        print(f"✅ {description}: {len(data['data'])} accounts")
                    elif endpoint == "transactions" and "data" in data:
                        print(f"✅ {description}: {len(data['data'])} transactions")
                    else:
                        print(f"✅ {description}: OK")
                else:
                    print(f"❌ {description}: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"❌ {description}: ERROR - {str(e)}")
        
        print()
    
    def test_file_upload(self):
        """Test file upload functionality."""
        print("📤 Testing File Upload...")
        print("-" * 40)
        
        try:
            # Create a test file
            test_content = "This is a test file for DHI Analytics Dashboard"
            test_filename = "test_upload.txt"
            
            files = {
                'file': (test_filename, test_content, 'text/plain')
            }
            
            response = requests.post(f"{self.frontend_url}/api/upload", files=files, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ File Upload: SUCCESS")
                print(f"   📁 Filename: {result.get('filename')}")
                print(f"   📊 Size: {result.get('size')} bytes")
                print(f"   🏷️ Type: {result.get('content_type')}")
            else:
                print(f"❌ File Upload: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ File Upload: ERROR - {str(e)}")
        
        print()
    
    def test_settings(self):
        """Test settings functionality."""
        print("⚙️ Testing Settings...")
        print("-" * 40)
        
        try:
            # Test GET settings
            response = requests.get(f"{self.frontend_url}/api/settings", timeout=5)
            if response.status_code == 200:
                settings = response.json()
                print("✅ Get Settings: OK")
                print(f"   📊 Settings loaded: {len(settings.get('settings', {}))} items")
            else:
                print(f"❌ Get Settings: HTTP {response.status_code}")
            
            # Test POST settings
            test_settings = {
                "plaid_api_url": "http://localhost:8080",
                "neo4j_url": "bolt://localhost:7687",
                "refresh_interval": 30,
                "theme": "light",
                "test_setting": True
            }
            
            response = requests.post(
                f"{self.frontend_url}/api/settings", 
                json=test_settings, 
                timeout=5
            )
            
            if response.status_code == 200:
                print("✅ Save Settings: OK")
            else:
                print(f"❌ Save Settings: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Settings Test: ERROR - {str(e)}")
        
        print()
    
    def show_dashboard_info(self):
        """Show dashboard information and features."""
        print("📊 DASHBOARD FEATURES OVERVIEW")
        print("=" * 50)
        
        features = [
            ("📈 Real-time Analytics", "Live transaction data visualization"),
            ("📱 Mobile Responsive", "Optimized for phones and tablets"),
            ("📷 Camera Capture", "Take photos directly in the app"),
            ("🎙️ Audio Recording", "Record voice notes and audio"),
            ("📤 File Upload", "Drag & drop file management"),
            ("🔄 PWA Support", "Install as native app"),
            ("🌐 Offline Mode", "Works without internet connection"),
            ("📊 Interactive Charts", "Dynamic data visualization"),
            ("🔍 API Monitoring", "Real-time service status"),
            ("⚡ Fast Performance", "Optimized for speed"),
        ]
        
        for feature, description in features:
            print(f"  {feature:<20} {description}")
        
        print()
        print("📱 MOBILE FEATURES:")
        print("  • Touch-optimized interface")
        print("  • Swipe navigation")
        print("  • Camera switching (front/back)")
        print("  • Voice recording")
        print("  • Gesture support")
        print("  • Push notifications")
        print()
        
        print("🌐 ACCESS URLS:")
        print(f"  • Dashboard:    {self.frontend_url}")
        print(f"  • API Docs:     {self.frontend_url}/docs")
        print(f"  • Plaid API:    {self.plaid_url}")
        print()
    
    def show_usage_examples(self):
        """Show usage examples."""
        print("💡 USAGE EXAMPLES")
        print("=" * 50)
        
        examples = [
            ("View Dashboard", f"Open {self.frontend_url} in your browser"),
            ("Monitor APIs", "Click 'API Status' in the sidebar"),
            ("Take Photos", "Go to 'Media Capture' → Start Camera → Take Photo"),
            ("Record Audio", "Go to 'Audio Recording' → Click red button"),
            ("Upload Files", "Go to 'File Upload' → Drag files or click to select"),
            ("View Analytics", "Go to 'Analytics' for advanced insights"),
            ("Mobile Access", "Open on phone and add to home screen"),
            ("Offline Use", "Works even without internet after first load")
        ]
        
        for i, (action, instruction) in enumerate(examples, 1):
            print(f"  {i}. {action}:")
            print(f"     {instruction}")
            print()
    
    def run_demo(self):
        """Run the complete demo."""
        print("🚀 DHI FRONTEND DASHBOARD DEMO")
        print("=" * 50)
        print()
        
        # Check services
        frontend_ok, plaid_ok = self.check_services()
        
        if frontend_ok:
            self.test_api_endpoints()
            
            if plaid_ok:
                self.test_plaid_proxy()
            
            self.test_file_upload()
            self.test_settings()
        
        self.show_dashboard_info()
        self.show_usage_examples()
        
        if frontend_ok:
            print("🎉 DEMO COMPLETED SUCCESSFULLY!")
            print(f"🌐 Open {self.frontend_url} to explore the dashboard")
        else:
            print("⚠️ DEMO COMPLETED WITH ISSUES")
            print("💡 Run './scripts/start_frontend.sh' to start the server")
        
        print()

def main():
    """Main demo function."""
    demo = FrontendDemo()
    demo.run_demo()

if __name__ == "__main__":
    main()
