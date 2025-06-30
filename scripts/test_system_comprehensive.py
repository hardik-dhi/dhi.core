#!/usr/bin/env python3
"""
DHI Core - Comprehensive Testing Script

This script tests all major functionalities of the DHI Core system
and provides a complete overview of current capabilities.
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class DHICoreSystemTester:
    """Comprehensive system testing for DHI Core."""
    
    def __init__(self, base_url: str = "http://localhost:8000", frontend_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.frontend_url = frontend_url
        self.session = self._create_session()
        self.test_results = {}
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
        
    def print_header(self, title: str):
        """Print formatted header."""
        print(f"\n{'='*70}")
        print(f"🧪 {title}")
        print(f"{'='*70}")
        
    def print_section(self, title: str):
        """Print formatted section."""
        print(f"\n{'-'*50}")
        print(f"📋 {title}")
        print(f"{'-'*50}")
        
    def print_test(self, test_name: str, status: str, details: str = ""):
        """Print test result."""
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{emoji} {test_name}: {status}")
        if details:
            print(f"   {details}")
            
    def record_test(self, category: str, test_name: str, status: str, details: Dict = None):
        """Record test result."""
        if category not in self.test_results:
            self.test_results[category] = []
        self.test_results[category].append({
            "test": test_name,
            "status": status,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })

    def test_api_health(self) -> bool:
        """Test basic API health."""
        try:
            response = self.session.get(f"{self.base_url}/docs", timeout=5)
            if response.status_code == 200:
                self.print_test("API Documentation", "PASS", "FastAPI docs accessible")
                self.record_test("infrastructure", "api_docs", "PASS")
                return True
            else:
                self.print_test("API Documentation", "FAIL", f"Status: {response.status_code}")
                self.record_test("infrastructure", "api_docs", "FAIL", {"status_code": response.status_code})
                return False
        except Exception as e:
            self.print_test("API Documentation", "FAIL", f"Error: {str(e)}")
            self.record_test("infrastructure", "api_docs", "FAIL", {"error": str(e)})
            return False

    def test_file_upload(self) -> bool:
        """Test file upload functionality."""
        try:
            # Create a temporary test file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("This is a test document for DHI Core system testing.")
                temp_file_path = f.name
            
            # Test file upload
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test_document.txt', f, 'text/plain')}
                data = {'media_type': 'text'}
                response = self.session.post(f"{self.base_url}/upload", files=files, data=data)
            
            # Clean up
            os.unlink(temp_file_path)
            
            if response.status_code == 200:
                result = response.json()
                self.print_test("File Upload", "PASS", f"Document ID: {result.get('document_id', 'N/A')}")
                self.record_test("core_functionality", "file_upload", "PASS", result)
                return True
            else:
                self.print_test("File Upload", "FAIL", f"Status: {response.status_code}")
                self.record_test("core_functionality", "file_upload", "FAIL", {"status_code": response.status_code})
                return False
                
        except Exception as e:
            self.print_test("File Upload", "FAIL", f"Error: {str(e)}")
            self.record_test("core_functionality", "file_upload", "FAIL", {"error": str(e)})
            return False

    def test_text_embedding(self) -> bool:
        """Test text embedding functionality."""
        try:
            data = {'text': 'This is a test text for embedding generation.'}
            response = self.session.post(f"{self.base_url}/embed-text", data=data)
            
            if response.status_code == 200:
                result = response.json()
                embedding = result.get('embedding', [])
                if embedding and isinstance(embedding, list) and len(embedding) > 0:
                    self.print_test("Text Embedding", "PASS", f"Embedding dimension: {len(embedding)}")
                    self.record_test("ai_ml", "text_embedding", "PASS", {"dimension": len(embedding)})
                    return True
                else:
                    self.print_test("Text Embedding", "FAIL", "Invalid embedding format")
                    self.record_test("ai_ml", "text_embedding", "FAIL", {"reason": "invalid_format"})
                    return False
            else:
                self.print_test("Text Embedding", "FAIL", f"Status: {response.status_code}")
                self.record_test("ai_ml", "text_embedding", "FAIL", {"status_code": response.status_code})
                return False
                
        except Exception as e:
            self.print_test("Text Embedding", "FAIL", f"Error: {str(e)}")
            self.record_test("ai_ml", "text_embedding", "FAIL", {"error": str(e)})
            return False

    def test_semantic_search(self) -> bool:
        """Test semantic search functionality."""
        try:
            params = {'q': 'test document', 'limit': 5}
            response = self.session.get(f"{self.base_url}/search", params=params)
            
            if response.status_code == 200:
                result = response.json()
                results = result.get('results', [])
                self.print_test("Semantic Search", "PASS", f"Found {len(results)} results")
                self.record_test("search", "semantic_search", "PASS", {"result_count": len(results)})
                return True
            else:
                self.print_test("Semantic Search", "FAIL", f"Status: {response.status_code}")
                self.record_test("search", "semantic_search", "FAIL", {"status_code": response.status_code})
                return False
                
        except Exception as e:
            self.print_test("Semantic Search", "FAIL", f"Error: {str(e)}")
            self.record_test("search", "semantic_search", "FAIL", {"error": str(e)})
            return False

    def test_plaid_integration(self) -> bool:
        """Test Plaid API integration."""
        try:
            # Test link token creation
            data = {'user_id': 'test_user_123', 'client_name': 'DHI Core Test'}
            response = self.session.post(f"{self.base_url}/plaid/link-token", json=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'link_token' in result:
                    self.print_test("Plaid Link Token", "PASS", "Link token generated successfully")
                    self.record_test("plaid", "link_token", "PASS", {"has_token": True})
                    return True
                else:
                    self.print_test("Plaid Link Token", "FAIL", "No link token in response")
                    self.record_test("plaid", "link_token", "FAIL", {"reason": "no_token"})
                    return False
            else:
                self.print_test("Plaid Link Token", "WARN", f"Status: {response.status_code} (May need Plaid configuration)")
                self.record_test("plaid", "link_token", "WARN", {"status_code": response.status_code})
                return False
                
        except Exception as e:
            self.print_test("Plaid Link Token", "WARN", f"Error: {str(e)} (May need Plaid configuration)")
            self.record_test("plaid", "link_token", "WARN", {"error": str(e)})
            return False

    def test_graph_operations(self) -> bool:
        """Test graph database operations."""
        try:
            # Test entity neighbor query
            entity_name = "test_entity"
            response = self.session.get(f"{self.base_url}/graph/entity/{entity_name}")
            
            if response.status_code == 200:
                result = response.json()
                neighbors = result.get('neighbors', [])
                self.print_test("Graph Entity Query", "PASS", f"Found {len(neighbors)} neighbors")
                self.record_test("graph", "entity_query", "PASS", {"neighbor_count": len(neighbors)})
                return True
            else:
                self.print_test("Graph Entity Query", "FAIL", f"Status: {response.status_code}")
                self.record_test("graph", "entity_query", "FAIL", {"status_code": response.status_code})
                return False
                
        except Exception as e:
            self.print_test("Graph Entity Query", "FAIL", f"Error: {str(e)}")
            self.record_test("graph", "entity_query", "FAIL", {"error": str(e)})
            return False

    def test_frontend_health(self) -> bool:
        """Test frontend application health."""
        try:
            response = self.session.get(f"{self.frontend_url}/", timeout=5)
            if response.status_code == 200:
                self.print_test("Frontend Application", "PASS", "Frontend accessible")
                self.record_test("frontend", "accessibility", "PASS")
                return True
            else:
                self.print_test("Frontend Application", "FAIL", f"Status: {response.status_code}")
                self.record_test("frontend", "accessibility", "FAIL", {"status_code": response.status_code})
                return False
        except Exception as e:
            self.print_test("Frontend Application", "WARN", f"Error: {str(e)} (Frontend may not be running)")
            self.record_test("frontend", "accessibility", "WARN", {"error": str(e)})
            return False

    def test_database_connectivity(self) -> bool:
        """Test database connectivity through API endpoints."""
        try:
            # Test that requires database operation (document listing)
            test_doc_id = "test-document-id"
            response = self.session.get(f"{self.base_url}/document/{test_doc_id}/chunks")
            
            # We expect this to work (even if no document exists)
            if response.status_code in [200, 404]:  # 404 is OK - document doesn't exist
                self.print_test("Database Connectivity", "PASS", "Database operations functional")
                self.record_test("database", "connectivity", "PASS")
                return True
            else:
                self.print_test("Database Connectivity", "FAIL", f"Status: {response.status_code}")
                self.record_test("database", "connectivity", "FAIL", {"status_code": response.status_code})
                return False
                
        except Exception as e:
            self.print_test("Database Connectivity", "FAIL", f"Error: {str(e)}")
            self.record_test("database", "connectivity", "FAIL", {"error": str(e)})
            return False

    def run_comprehensive_tests(self):
        """Run all system tests."""
        self.print_header("DHI Core - Comprehensive System Testing")
        print("🎯 Testing all major functionalities and integrations")
        print(f"🌐 API Base URL: {self.base_url}")
        print(f"🖥️  Frontend URL: {self.frontend_url}")
        print(f"⏰ Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Infrastructure Tests
        self.print_section("Infrastructure & Connectivity")
        self.test_api_health()
        self.test_database_connectivity()
        self.test_frontend_health()
        
        # Core Functionality Tests
        self.print_section("Core Functionality")
        self.test_file_upload()
        self.test_text_embedding()
        self.test_semantic_search()
        
        # Advanced Features Tests
        self.print_section("Advanced Features")
        self.test_graph_operations()
        self.test_plaid_integration()
        
        # Generate Test Report
        self.print_section("Test Results Summary")
        self.generate_test_report()

    def generate_test_report(self):
        """Generate comprehensive test report."""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warning_tests = 0
        
        for category, tests in self.test_results.items():
            category_passed = sum(1 for t in tests if t['status'] == 'PASS')
            category_failed = sum(1 for t in tests if t['status'] == 'FAIL')
            category_warnings = sum(1 for t in tests if t['status'] == 'WARN')
            category_total = len(tests)
            
            total_tests += category_total
            passed_tests += category_passed
            failed_tests += category_failed
            warning_tests += category_warnings
            
            print(f"\n📊 {category.replace('_', ' ').title()}: {category_passed}/{category_total} passed")
            for test in tests:
                status_emoji = "✅" if test['status'] == 'PASS' else "❌" if test['status'] == 'FAIL' else "⚠️"
                print(f"   {status_emoji} {test['test']}")
        
        print(f"\n{'='*50}")
        print(f"📈 OVERALL RESULTS")
        print(f"{'='*50}")
        print(f"✅ Total Passed: {passed_tests}")
        print(f"❌ Total Failed: {failed_tests}")
        print(f"⚠️  Total Warnings: {warning_tests}")
        print(f"📊 Total Tests: {total_tests}")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"🎯 Success Rate: {success_rate:.1f}%")
        
        # Save detailed results
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "warnings": warning_tests,
                    "success_rate": success_rate,
                    "timestamp": datetime.now().isoformat()
                },
                "detailed_results": self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Print recommendations
        print(f"\n{'='*50}")
        print(f"💡 RECOMMENDATIONS")
        print(f"{'='*50}")
        
        if failed_tests == 0 and warning_tests == 0:
            print("🎉 Excellent! All systems are operational.")
            print("🚀 Your DHI Core installation is ready for production use.")
        elif failed_tests == 0:
            print("👍 Core functionality is working well.")
            print("⚠️  Some optional features need configuration (warnings above).")
        else:
            print("🔧 Some critical issues need attention:")
            for category, tests in self.test_results.items():
                failed_in_category = [t for t in tests if t['status'] == 'FAIL']
                if failed_in_category:
                    print(f"   • {category.replace('_', ' ').title()}: {len(failed_in_category)} issue(s)")
        
        print(f"\n📚 For troubleshooting help, see:")
        print(f"   • TESTING_GUIDE.md")
        print(f"   • CURRENT_STATUS.md")
        print(f"   • README.md")

def main():
    """Main function to run tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DHI Core System Tester")
    parser.add_argument("--api-url", default="http://localhost:8000", 
                       help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--frontend-url", default="http://localhost:8081", 
                       help="Frontend URL (default: http://localhost:8081)")
    
    args = parser.parse_args()
    
    tester = DHICoreSystemTester(base_url=args.api_url, frontend_url=args.frontend_url)
    tester.run_comprehensive_tests()

if __name__ == "__main__":
    main()
