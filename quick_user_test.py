#!/usr/bin/env python3
"""
Simple test for user list API
"""

import requests
import json

BASE_URL = "https://rockmartialartsacademy.com"

def quick_test():
    print("🔍 Quick User List API Test")
    
    # Get superadmin token
    print("1. Getting superadmin token...")
    try:
        admin_login = {
            "email": "testsuperadmin@example.com",
            "password": "TestSuperAdmin123!"
        }
        
        response = requests.post(f"{BASE_URL}/api/superadmin/login", json=admin_login, timeout=10)
        print(f"   Login status: {response.status_code}")
        
        if response.status_code == 200:
            token = response.json()["data"]["token"]
            print("   ✅ Token obtained")
            
            # Test user list
            print("\n2. Testing user list...")
            headers = {"Authorization": f"Bearer {token}"}
            user_response = requests.get(f"{BASE_URL}/api/users?limit=5", headers=headers, timeout=10)
            print(f"   User list status: {user_response.status_code}")
            
            if user_response.status_code == 200:
                data = user_response.json()
                print(f"   ✅ Success! Found {data.get('total', 0)} users")
                print(f"   📊 Retrieved {len(data.get('users', []))} users in response")
            else:
                print(f"   ❌ Error: {user_response.text}")
        else:
            print(f"   ❌ Login failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    quick_test()
