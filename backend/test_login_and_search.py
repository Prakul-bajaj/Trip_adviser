import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def login():
    """Login with your registered user"""
    print("\n" + "="*60)
    print("  LOGIN")
    print("="*60)
    
    url = f"{BASE_URL}/api/users/login/"
    data = {
        "email": "testuser123@example.com",  # Change this to your email
        "password": "SecurePass123!"      # Change this to your password
    }
    
    print(f"\nLogging in as: {data['email']}")
    
    try:
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Login successful!")
            print(f"User: {result['user']['email']}")
            print(f"Name: {result['user']['first_name']} {result['user']['last_name']}")
            return result['tokens']['access']
        else:
            print("❌ Login failed!")
            print(f"Response: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def get_spiritual_places():
    """Get all spiritual destinations"""
    print("\n" + "="*60)
    print("  SPIRITUAL DESTINATIONS")
    print("="*60)
    
    url = f"{BASE_URL}/api/destinations/spiritual/"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            destinations = data if isinstance(data, list) else data.get('results', [])
            
            print(f"\n✅ Found {len(destinations)} spiritual destinations!\n")
            
            for i, dest in enumerate(destinations, 1):
                print(f"{i}. {dest['name']}, {dest['state']}")
                print(f"   Focus: {', '.join(dest.get('spiritual_focus', []))}")
                print(f"   Budget: ₹{dest.get('budget_range_min', 0):,} - ₹{dest.get('budget_range_max', 0):,}")
                print(f"   Duration: {dest.get('typical_duration', 0)} days")
                print()
                
            return destinations
        else:
            print(f"❌ Failed to get destinations")
            print(f"Status: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []


def search_spiritual_places(focus=None, state=None, budget_max=None):
    """Search spiritual places with filters"""
    print("\n" + "="*60)
    print("  SEARCH SPIRITUAL PLACES")
    print("="*60)
    
    url = f"{BASE_URL}/api/destinations/spiritual/search/?"
    params = []
    
    if focus:
        params.append(f"focus={focus}")
    if state:
        params.append(f"state={state}")
    if budget_max:
        params.append(f"budget_max={budget_max}")
    
    url += "&".join(params)
    
    print(f"\nSearching with: Focus={focus}, State={state}, Budget Max={budget_max}")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json()
            destinations = result.get('results', [])
            count = result.get('count', len(destinations))
            
            print(f"\n✅ Found {count} results!\n")
            
            for dest in destinations:
                print(f"📿 {dest['name']}")
                print(f"   Location: {dest['state']}, {dest['country']}")
                print(f"   Focus: {', '.join(dest.get('spiritual_focus', []))}")
                print(f"   Best Time: {', '.join(dest.get('best_time_to_visit', [])[:3])}")
                print()
                
            return destinations
        else:
            print(f"❌ Search failed")
            return []
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []


def get_all_destinations():
    """Get all destinations (not just spiritual)"""
    print("\n" + "="*60)
    print("  ALL DESTINATIONS")
    print("="*60)
    
    url = f"{BASE_URL}/api/destinations/"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            destinations = data.get('results', data) if isinstance(data, dict) else data
            
            print(f"\n✅ Found {len(destinations)} total destinations!\n")
            
            # Group by category
            categories = {}
            for dest in destinations:
                exp_types = dest.get('experience_types', [])
                for exp in exp_types:
                    if exp not in categories:
                        categories[exp] = []
                    categories[exp].append(dest['name'])
            
            for category, places in categories.items():
                print(f"\n{category}: {len(places)} places")
                for place in places[:3]:
                    print(f"  • {place}")
                    
            return destinations
        else:
            print(f"❌ Failed to get destinations")
            return []
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []


def update_preferences(token):
    """Update travel preferences"""
    print("\n" + "="*60)
    print("  UPDATE TRAVEL PREFERENCES")
    print("="*60)
    
    url = f"{BASE_URL}/api/users/preferences/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "preferred_geographies": ["Himalayan", "Coastal", "Urban"],
        "preferred_experiences": ["Spiritual", "Adventure", "Cultural"],
        "spiritual_interests": ["hinduism", "buddhism", "yoga"],
        "typical_budget_range": "10000-30000",
        "typical_trip_duration": 5,
        "preferred_climates": ["Temperate", "Tropical"]
    }
    
    try:
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Preferences updated!")
            print(f"Spiritual Interests: {', '.join(result.get('spiritual_interests', []))}")
            print(f"Budget Range: {result.get('typical_budget_range')}")
            return True
        else:
            print(f"❌ Failed to update preferences")
            print(response.json())
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    print("\n" + "🕉️ "*30)
    print("  TRIP ADVISER - SPIRITUAL DESTINATIONS TEST")
    print("🕉️ "*30)
    
    # 1. Login
    token = login()
    
    if not token:
        print("\n❌ Cannot proceed without login. Please check your credentials.")
        print("Update the email/password in the script if needed.")
        return
    
    print(f"\n💡 Access Token: {token[:50]}...")
    
    # 2. Get all spiritual destinations
    spiritual_dests = get_spiritual_places()
    
    # 3. Get all destinations
    all_dests = get_all_destinations()
    
    # 4. Search for Hindu spiritual places
    print("\n" + "-"*60)
    hindu_places = search_spiritual_places(focus="hinduism")
    
    # 5. Search by state
    print("\n" + "-"*60)
    uttarakhand_places = search_spiritual_places(state="Uttarakhand")
    
    # 6. Search by budget
    print("\n" + "-"*60)
    budget_places = search_spiritual_places(budget_max=20000)
    
    # 7. Update preferences
    update_preferences(token)
    
    print("\n" + "="*60)
    print("  ✅ ALL TESTS COMPLETED!")
    print("="*60)
    
    print("\n📊 Summary:")
    print(f"  • Total Destinations: {len(all_dests)}")
    print(f"  • Spiritual Destinations: {len(spiritual_dests)}")
    print(f"  • Your Token: {token[:50]}...")
    
    print("\n💡 Next Steps:")
    print("  1. Use the token for authenticated requests")
    print("  2. Build a frontend to display these destinations")
    print("  3. Implement the chatbot for recommendations")
    print()


if __name__ == "__main__":
    main()