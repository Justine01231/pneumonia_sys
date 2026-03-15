"""
Quick test script to verify the dashboard API endpoints
"""

import requests
import json

base_url = "http://localhost:5000"

print("Testing MediScan API Endpoints...")
print("=" * 50)

# Test 1: Dashboard Stats
print("\n1. Testing /api/dashboard/stats")
try:
    response = requests.get(f"{base_url}/api/dashboard/stats")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Total Scans: {data.get('total_scans', 0)}")
        print(f"   ✓ Patients Today: {data.get('patients_today', 0)}")
        print(f"   ✓ Normal Count: {data.get('normal_count', 0)}")
        print(f"   ✓ Pneumonia Count: {data.get('pneumonia_count', 0)}")
    else:
        print(f"   ✗ Error: {response.text}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: Recent Patients
print("\n2. Testing /api/patients/recent")
try:
    response = requests.get(f"{base_url}/api/patients/recent")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {len(data)} recent patients")
        if len(data) > 0:
            print(f"   First patient: {data[0]}")
    else:
        print(f"   ✗ Error: {response.text}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 3: History
print("\n3. Testing /api/history")
try:
    response = requests.get(f"{base_url}/api/history")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Found {len(data)} history records")
    else:
        print(f"   ✗ Error: {response.text}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 50)
print("Testing complete!")
