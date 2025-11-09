import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("\n" + "="*60)
print("  TESTING USER REGISTRATION")
print("="*60)

url = f"{BASE_URL}/api/users/register/"
data = {
    "email": "testuser123@example.com",
    "username": "testuser123",
    "first_name": "Test",
    "last_name": "User",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "phone_number": "9876543210"
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("\n✅ SUCCESS! User registered!")
        tokens = response.json()['tokens']
        print(f"\nAccess Token: {tokens['access'][:50]}...")
    else:
        print("\n❌ FAILED!")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")