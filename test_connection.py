#!/usr/bin/env python3
"""
Test script to verify frontend-backend connection for competitor backlink spy
"""
import requests
import json

def test_api_connection():
    base_url = "http://localhost:8882"
    
    print("Testing API connection...")
    
    # Test 1: Basic API info endpoint
    try:
        response = requests.get(f"{base_url}/backlinkapi")
        if response.status_code == 200:
            print("✅ API info endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ API info endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API info endpoint error: {e}")
    
    # Test 2: Competitor analysis endpoint
    try:
        payload = {
            "your_domain": "testdomain.com",
            "competitors": ["competitor1.com", "competitor2.com"],
            "min_da": 30
        }
        
        response = requests.post(
            f"{base_url}/backlinkapi/competitors/analyze",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Competitor analysis endpoint working")
            print(f"   Found {len(data.get('gaps', []))} gap opportunities")
            print(f"   Generated {len(data.get('content_opportunities', []))} content opportunities")
            print(f"   Summary: {data.get('summary', {})}")
        else:
            print(f"❌ Competitor analysis endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Competitor analysis endpoint error: {e}")
    
    # Test 3: Frontend accessibility
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Frontend accessible")
            if "Competitor Backlink Spy" in response.text:
                print("✅ Competitor Spy section found in frontend")
            else:
                print("⚠️  Competitor Spy section not found in frontend")
        else:
            print(f"❌ Frontend not accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Frontend accessibility error: {e}")

if __name__ == "__main__":
    test_api_connection()
