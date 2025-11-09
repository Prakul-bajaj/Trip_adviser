import requests
import json
from collections import defaultdict

BASE_URL = "http://127.0.0.1:8000"

# Update these credentials
EMAIL = "user1761677535@example.com"
PASSWORD = "SecurePass123!"
TOKEN = None


def login():
    """Login to get token"""
    global TOKEN
    url = f"{BASE_URL}/api/users/login/"
    data = {"email": EMAIL, "password": PASSWORD}
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            TOKEN = result['tokens']['access']
            print(f"✅ Logged in as: {EMAIL}\n")
            return True
        else:
            print("❌ Login failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def get_all_destinations():
    """Get ALL destinations"""
    print("\n" + "="*90)
    print("  🌍 ALL TRAVEL DESTINATIONS DATABASE")
    print("="*90)
    
    url = f"{BASE_URL}/api/destinations/"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            destinations = data if isinstance(data, list) else data.get('results', [])
            
            print(f"\n✅ Total Destinations: {len(destinations)}\n")
            print("-"*90)
            
            for i, dest in enumerate(destinations, 1):
                print(f"\n{i}. 📍 {dest['name'].upper()}")
                print(f"{'─'*90}")
                
                # Basic Info
                print(f"📌 Location: {dest.get('state', 'N/A')}, {dest.get('country', 'India')}")
                print(f"📝 Description: {dest.get('description', 'N/A')[:100]}...")
                
                # Categories
                if dest.get('experience_types'):
                    print(f"🎭 Experiences: {', '.join(dest.get('experience_types', []))}")
                
                if dest.get('geography_types'):
                    print(f"🗺️  Geography: {', '.join(dest.get('geography_types', []))}")
                
                if dest.get('landscape_types'):
                    print(f"🏔️  Landscape: {', '.join(dest.get('landscape_types', []))}")
                
                if dest.get('spiritual_focus'):
                    print(f"🕉️  Spiritual: {', '.join(dest.get('spiritual_focus', []))}")
                
                # Budget & Duration
                budget_min = dest.get('budget_range_min', 0)
                budget_max = dest.get('budget_range_max', 0)
                print(f"💰 Budget: ₹{budget_min:,} - ₹{budget_max:,}")
                print(f"📅 Duration: {dest.get('typical_duration')} days")
                
                # Climate & Location
                print(f"🌡️  Climate: {dest.get('climate_type', 'N/A')} ({dest.get('average_temperature_range', 'N/A')})")
                print(f"⛰️  Altitude: {dest.get('altitude', 0):,}m")
                
                # Best Time
                if dest.get('best_time_to_visit'):
                    months = ', '.join(dest.get('best_time_to_visit', [])[:4])
                    print(f"📆 Best Time: {months}")
                
                # Ratings
                print(f"⚡ Difficulty: {dest.get('difficulty_level', 'N/A').capitalize()}")
                print(f"🛡️  Safety: {dest.get('safety_rating', 0)}/5.0")
                print(f"⭐ Popularity: {dest.get('popularity_score', 0)}/100")
                
                print("-"*90)
            
            return destinations
        else:
            print(f"❌ Failed to fetch destinations: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def search_by_experience(experience_type):
    """Search destinations by experience type"""
    print("\n" + "="*90)
    print(f"  🎯 DESTINATIONS BY EXPERIENCE: {experience_type.upper()}")
    print("="*90)
    
    url = f"{BASE_URL}/api/destinations/experience/{experience_type}/"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            destinations = data.get('results', [])
            
            print(f"\n✅ Found {len(destinations)} destinations\n")
            
            for dest in destinations:
                budget = f"₹{dest.get('budget_range_min', 0):,}-{dest.get('budget_range_max', 0):,}"
                print(f"📍 {dest['name']}, {dest['state']}")
                print(f"   Budget: {budget} | Duration: {dest.get('typical_duration')} days | Difficulty: {dest.get('difficulty_level')}")
                print()
            
            return destinations
        else:
            print(f"❌ Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def search_by_geography(geography_type):
    """Search destinations by geography"""
    print("\n" + "="*90)
    print(f"  🗺️  DESTINATIONS BY GEOGRAPHY: {geography_type.upper()}")
    print("="*90)
    
    url = f"{BASE_URL}/api/destinations/geography/{geography_type}/"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            destinations = data.get('results', [])
            
            print(f"\n✅ Found {len(destinations)} destinations\n")
            
            for dest in destinations:
                print(f"📍 {dest['name']}, {dest['state']}")
                print(f"   Experiences: {', '.join(dest.get('experience_types', [])[:3])}")
                print(f"   Best Time: {', '.join(dest.get('best_time_to_visit', [])[:3])}")
                print()
            
            return destinations
        else:
            print(f"❌ Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def search_by_landscape(landscape_type):
    """Search destinations by landscape"""
    print("\n" + "="*90)
    print(f"  🏔️  DESTINATIONS BY LANDSCAPE: {landscape_type.upper()}")
    print("="*90)
    
    url = f"{BASE_URL}/api/destinations/landscape/{landscape_type}/"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            destinations = data.get('results', [])
            
            print(f"\n✅ Found {len(destinations)} destinations\n")
            
            for dest in destinations:
                print(f"📍 {dest['name']}, {dest['state']}")
                print(f"   Climate: {dest.get('climate_type')} | Altitude: {dest.get('altitude', 0):,}m")
                print()
            
            return destinations
        else:
            print(f"❌ Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def advanced_search(filters):
    """Advanced search with multiple filters"""
    print("\n" + "="*90)
    print("  🔍 ADVANCED SEARCH")
    print("="*90)
    
    url = f"{BASE_URL}/api/destinations/search/"
    
    filter_desc = " | ".join([f"{k}: {v}" for k, v in filters.items()])
    print(f"\n🔎 Filters: {filter_desc}\n")
    
    try:
        response = requests.get(url, params=filters)
        
        if response.status_code == 200:
            data = response.json()
            destinations = data.get('results', [])
            
            print(f"✅ Found {len(destinations)} matching destinations\n")
            
            for dest in destinations:
                budget = f"₹{dest.get('budget_range_min', 0):,} - ₹{dest.get('budget_range_max', 0):,}"
                print(f"📍 {dest['name']}, {dest['state']}")
                print(f"   Budget: {budget} | Duration: {dest.get('typical_duration')} days")
                print(f"   Experiences: {', '.join(dest.get('experience_types', [])[:3])}")
                print()
            
            return destinations
        else:
            print(f"❌ Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def get_all_categories():
    """Get all available categories"""
    print("\n" + "="*90)
    print("  📊 AVAILABLE CATEGORIES")
    print("="*90)
    
    url = f"{BASE_URL}/api/destinations/categories/"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ Total Destinations: {data.get('total_destinations', 0)}\n")
            
            print("🎭 EXPERIENCE TYPES:")
            for exp in data.get('experience_types', []):
                print(f"   • {exp}")
            
            print("\n🗺️  GEOGRAPHY TYPES:")
            for geo in data.get('geography_types', []):
                print(f"   • {geo}")
            
            print("\n🏔️  LANDSCAPE TYPES:")
            for land in data.get('landscape_types', []):
                print(f"   • {land}")
            
            print("\n🕉️  SPIRITUAL FOCUS:")
            for spirit in data.get('spiritual_focus', []):
                print(f"   • {spirit}")
            
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}


def categorize_by_state(destinations):
    """Categorize destinations by state"""
    print("\n" + "="*90)
    print("  🗺️  DESTINATIONS BY STATE")
    print("="*90 + "\n")
    
    by_state = defaultdict(list)
    for dest in destinations:
        state = dest.get('state', 'Unknown')
        by_state[state].append(dest)
    
    for state, dests in sorted(by_state.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n📍 {state.upper()} ({len(dests)} destinations)")
        print("-"*90)
        for dest in dests[:5]:  # Show top 5 per state
            budget = f"₹{dest.get('budget_range_min', 0):,}-{dest.get('budget_range_max', 0):,}"
            print(f"  • {dest['name']}")
            print(f"    Budget: {budget} | Duration: {dest.get('typical_duration')} days")
            print(f"    Experiences: {', '.join(dest.get('experience_types', [])[:3])}")
        if len(dests) > 5:
            print(f"  ... and {len(dests) - 5} more")
        print()


def categorize_by_budget(destinations):
    """Categorize destinations by budget"""
    print("\n" + "="*90)
    print("  💰 DESTINATIONS BY BUDGET")
    print("="*90 + "\n")
    
    budget_ranges = {
        "Budget (Under ₹20k)": [],
        "Mid-Range (₹20k-50k)": [],
        "Premium (₹50k-100k)": [],
        "Luxury (₹100k+)": []
    }
    
    for dest in destinations:
        max_budget = dest.get('budget_range_max', 0)
        if max_budget < 20000:
            budget_ranges["Budget (Under ₹20k)"].append(dest)
        elif max_budget < 50000:
            budget_ranges["Mid-Range (₹20k-50k)"].append(dest)
        elif max_budget < 100000:
            budget_ranges["Premium (₹50k-100k)"].append(dest)
        else:
            budget_ranges["Luxury (₹100k+)"].append(dest)
    
    for range_name, dests in budget_ranges.items():
        if dests:
            print(f"\n💵 {range_name} ({len(dests)} destinations)")
            print("-"*90)
            for dest in dests[:5]:
                budget = f"₹{dest.get('budget_range_min', 0):,} - ₹{dest.get('budget_range_max', 0):,}"
                print(f"  • {dest['name']}, {dest['state']}")
                print(f"    Budget: {budget} | Duration: {dest.get('typical_duration')} days")
            if len(dests) > 5:
                print(f"  ... and {len(dests) - 5} more")
            print()


def categorize_by_difficulty(destinations):
    """Categorize by difficulty level"""
    print("\n" + "="*90)
    print("  ⚡ DESTINATIONS BY DIFFICULTY")
    print("="*90 + "\n")
    
    by_difficulty = defaultdict(list)
    for dest in destinations:
        difficulty = dest.get('difficulty_level', 'unknown')
        by_difficulty[difficulty].append(dest)
    
    icons = {'easy': '🟢', 'moderate': '🟡', 'difficult': '🔴', 'hard': '🔴'}
    
    for difficulty in ['easy', 'moderate', 'difficult', 'hard']:
        if difficulty in by_difficulty:
            dests = by_difficulty[difficulty]
            print(f"\n{icons.get(difficulty, '⚪')} {difficulty.upper()} ({len(dests)} destinations)")
            print("-"*90)
            for dest in dests[:5]:
                print(f"  • {dest['name']}, {dest['state']}")
                print(f"    Altitude: {dest.get('altitude', 0):,}m | Duration: {dest.get('typical_duration')} days")
            if len(dests) > 5:
                print(f"  ... and {len(dests) - 5} more")
            print()


def interactive_search():
    """Interactive chatbot-style search"""
    print("\n" + "="*90)
    print("  💬 INTERACTIVE DESTINATION FINDER")
    print("="*90)
    
    print("\nLet me help you find the perfect destination! 🌍")
    print("\nWhat are you looking for?")
    print("1. Adventure destinations")
    print("2. Beach/Coastal destinations")
    print("3. Mountain/Hill stations")
    print("4. Cultural/Historical places")
    print("5. Spiritual/Religious places")
    print("6. Wildlife/Nature destinations")
    print("7. Custom search")
    
    choice = input("\nEnter your choice (1-7): ").strip()
    
    filters = {}
    
    if choice == '1':
        filters['experience'] = 'Adventure'
    elif choice == '2':
        filters['geography'] = 'Coastal'
    elif choice == '3':
        filters['landscape'] = 'Mountains'
    elif choice == '4':
        filters['experience'] = 'Cultural'
    elif choice == '5':
        filters['spiritual'] = 'Hindu Temples'
    elif choice == '6':
        filters['experience'] = 'Wildlife'
    elif choice == '7':
        # Custom search
        print("\n📝 Custom Search Options:")
        
        q = input("Search keyword (or press Enter to skip): ").strip()
        if q:
            filters['q'] = q
        
        state = input("State (or press Enter to skip): ").strip()
        if state:
            filters['state'] = state
        
        budget = input("Max budget (or press Enter to skip): ").strip()
        if budget:
            filters['budget_max'] = budget
        
        duration = input("Max duration in days (or press Enter to skip): ").strip()
        if duration:
            filters['max_duration'] = duration
        
        difficulty = input("Difficulty (easy/moderate/difficult) (or press Enter to skip): ").strip()
        if difficulty:
            filters['difficulty'] = difficulty
    
    if filters:
        return advanced_search(filters)
    else:
        print("❌ No filters selected")
        return []


def generate_summary_report(destinations):
    """Generate comprehensive summary"""
    print("\n" + "="*90)
    print("  📈 COMPREHENSIVE SUMMARY REPORT")
    print("="*90 + "\n")
    
    total = len(destinations)
    
    # Budget stats
    budgets = [d.get('budget_range_max', 0) for d in destinations if d.get('budget_range_max')]
    avg_budget = sum(budgets) / len(budgets) if budgets else 0
    
    # Duration stats
    durations = [d.get('typical_duration', 0) for d in destinations if d.get('typical_duration')]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    print(f"📊 Total Destinations: {total}")
    print(f"\n💰 Budget Analysis:")
    print(f"   Average Maximum Budget: ₹{avg_budget:,.0f}")
    print(f"   Cheapest: ₹{min(budgets) if budgets else 0:,}")
    print(f"   Most Expensive: ₹{max(budgets) if budgets else 0:,}")
    
    print(f"\n📅 Duration Analysis:")
    print(f"   Average Trip Duration: {avg_duration:.1f} days")
    print(f"   Shortest: {min(durations) if durations else 0} days")
    print(f"   Longest: {max(durations) if durations else 0} days")
    
    # State distribution
    states = {}
    for dest in destinations:
        state = dest.get('state', 'Unknown')
        states[state] = states.get(state, 0) + 1
    
    print(f"\n🗺️  Top 10 States:")
    for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {state}: {count} destinations")
    
    # Difficulty distribution
    difficulty_dist = defaultdict(int)
    for dest in destinations:
        difficulty_dist[dest.get('difficulty_level', 'unknown')] += 1
    
    print(f"\n⚡ Difficulty Distribution:")
    for diff, count in difficulty_dist.items():
        percentage = (count / total) * 100
        print(f"   {diff.capitalize()}: {count} ({percentage:.1f}%)")
    
    print()


def main():
    # print("\n" + "🌍 "*45)
    print("  COMPREHENSIVE TRAVEL DESTINATIONS SEARCH TOOL")
    # print("🌍 "*45)
    
    if not login():
        return
    
    while True:
        print("\n" + "="*90)
        print("  🗺️  MAIN MENU")
        print("="*90)
        print("  1.  View All Destinations")
        print("  2.  Search by Experience Type")
        print("  3.  Search by Geography")
        print("  4.  Search by Landscape")
        print("  5.  View All Categories")
        print("  6.  Advanced Search")
        print("  7.  Interactive Search (Chatbot Style)")
        print("  8.  Group by State")
        print("  9.  Group by Budget")
        print("  10. Group by Difficulty")
        print("  11. Generate Summary Report")
        print("  0.  Exit")
        print("="*90)
        
        choice = input("\nEnter your choice (0-11): ").strip()
        
        if choice == '1':
            destinations = get_all_destinations()
        elif choice == '2':
            exp_type = input("Enter experience type (e.g., Adventure, Beach, Cultural): ").strip()
            destinations = search_by_experience(exp_type)
        elif choice == '3':
            geo_type = input("Enter geography type (e.g., Himalayan, Coastal): ").strip()
            destinations = search_by_geography(geo_type)
        elif choice == '4':
            land_type = input("Enter landscape type (e.g., Mountains, Beaches): ").strip()
            destinations = search_by_landscape(land_type)
        elif choice == '5':
            get_all_categories()
        elif choice == '6':
            print("\nEnter search filters (press Enter to skip any):")
            filters = {}
            q = input("Search keyword: ").strip()
            if q: filters['q'] = q
            state = input("State: ").strip()
            if state: filters['state'] = state
            budget = input("Max budget: ").strip()
            if budget: filters['budget_max'] = budget
            if filters:
                destinations = advanced_search(filters)
        elif choice == '7':
            destinations = interactive_search()
        elif choice == '8':
            destinations = get_all_destinations()
            if destinations:
                categorize_by_state(destinations)
        elif choice == '9':
            destinations = get_all_destinations()
            if destinations:
                categorize_by_budget(destinations)
        elif choice == '10':
            destinations = get_all_destinations()
            if destinations:
                categorize_by_difficulty(destinations)
        elif choice == '11':
            destinations = get_all_destinations()
            if destinations:
                generate_summary_report(destinations)
        elif choice == '0':
            print("\n👋 Thank you for using the travel search tool!")
            break
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    main()