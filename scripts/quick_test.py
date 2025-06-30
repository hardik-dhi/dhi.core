#!/usr/bin/env python3
"""
DHI Core - Quick Test Script

Quick smoke tests for the core functionalities to verify the system is working.
"""

import requests
import sys
import tempfile
import os

def test_api_basic():
    """Test basic API functionality."""
    try:
        print("🧪 Testing API Documentation...")
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API is accessible")
            return True
        else:
            print(f"❌ API not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False

def test_file_upload():
    """Test file upload."""
    try:
        print("🧪 Testing File Upload...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content for DHI Core")
            temp_file = f.name
        
        with open(temp_file, 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            data = {'media_type': 'text'}
            response = requests.post("http://localhost:8000/upload", files=files, data=data)
        
        os.unlink(temp_file)
        
        if response.status_code == 200:
            print("✅ File upload working")
            return True
        else:
            print(f"❌ File upload failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ File upload error: {e}")
        return False

def test_embedding():
    """Test text embedding."""
    try:
        print("🧪 Testing Text Embedding...")
        data = {'text': 'Test embedding generation'}
        response = requests.post("http://localhost:8000/embed-text", data=data)
        
        if response.status_code == 200:
            result = response.json()
            if 'embedding' in result and len(result['embedding']) > 0:
                print("✅ Text embedding working")
                return True
            else:
                print("❌ Invalid embedding response")
                return False
        else:
            print(f"❌ Embedding failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        return False

def test_search():
    """Test semantic search."""
    try:
        print("🧪 Testing Semantic Search...")
        response = requests.get("http://localhost:8000/search?q=test&limit=5")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Search working - found {len(result.get('results', []))} results")
            return True
        else:
            print(f"❌ Search failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Search error: {e}")
        return False

def main():
    """Run quick tests."""
    print("🚀 DHI Core - Quick Functionality Test")
    print("=" * 50)
    
    tests = [
        test_api_basic,
        test_file_upload,
        test_embedding,
        test_search
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All core functions working!")
        return 0
    elif passed >= total // 2:
        print("⚠️  Some issues detected but core system functional")
        return 1
    else:
        print("❌ Major issues detected - check system configuration")
        return 2

if __name__ == "__main__":
    sys.exit(main())
