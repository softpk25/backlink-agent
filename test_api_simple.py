import requests
import json

# Test API connection
try:
    # Test basic API endpoint
    r1 = requests.get('http://localhost:8882/backlinkapi')
    print(f"API Info Status: {r1.status_code}")
    if r1.status_code == 200:
        print(f"API Info Response: {r1.json()}")
    
    # Test competitor analysis endpoint
    payload = {
        "your_domain": "testdomain.com",
        "competitors": ["competitor1.com"],
        "min_da": 30
    }
    
    r2 = requests.post('http://localhost:8882/backlinkapi/competitors/analyze', json=payload)
    print(f"Competitor Analysis Status: {r2.status_code}")
    if r2.status_code == 200:
        data = r2.json()
        print(f"Found {len(data.get('gaps', []))} opportunities")
        print(f"Status: {data.get('status')}")
    else:
        print(f"Error: {r2.text}")
        
except Exception as e:
    print(f"Connection error: {e}")
