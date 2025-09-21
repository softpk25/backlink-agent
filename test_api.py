#!/usr/bin/env python3
"""
Simple test script for Prometrix SEO Agents API
Run this after starting the main server to test the endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health check endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health Check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
            print(f"Database: {data['database']}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_api_info():
    """Test API info endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api")
        print(f"\nAPI Info: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"API Name: {data['name']}")
            print(f"Version: {data['version']}")
            print(f"Description: {data['description']}")
        return response.status_code == 200
    except Exception as e:
        print(f"API info failed: {e}")
        return False

def test_backlinks_summary():
    """Test backlinks summary endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/backlinks/summary")
        print(f"\nBacklinks Summary: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total Backlinks: {data['cards']['total_backlinks']}")
            print(f"Referring Domains: {data['cards']['referring_domains']}")
            print(f"Average DA: {data['cards']['average_da']}")
            print(f"Toxic Links: {data['cards']['toxic_links']}")
        return response.status_code == 200
    except Exception as e:
        print(f"Backlinks summary failed: {e}")
        return False

def test_analyze_domain():
    """Test domain analysis endpoint"""
    try:
        payload = {
            "domain": "example.com",
            "source": "Ahrefs",
            "period": "30d"
        }
        response = requests.post(f"{BASE_URL}/api/analyze", json=payload)
        print(f"\nDomain Analysis: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Message: {data['message']}")
        return response.status_code == 200
    except Exception as e:
        print(f"Domain analysis failed: {e}")
        return False

def test_competitor_analysis():
    """Test competitor analysis endpoint"""
    try:
        payload = {
            "your_domain": "yourdomain.com",
            "competitors": ["competitor1.com", "competitor2.com"],
            "min_da": 30
        }
        response = requests.post(f"{BASE_URL}/api/competitors/analyze", json=payload)
        print(f"\nCompetitor Analysis: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Gap Opportunities: {len(data['gaps'])}")
        return response.status_code == 200
    except Exception as e:
        print(f"Competitor analysis failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Prometrix SEO Agents API...")
    print("=" * 50)
    
    tests = [
        test_health,
        test_api_info,
        test_backlinks_summary,
        test_analyze_domain,
        test_competitor_analysis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print("-" * 30)
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! API is working correctly.")
    else:
        print("❌ Some tests failed. Check the server logs for details.")

if __name__ == "__main__":
    main()
