#!/usr/bin/env python
import os
import sys
import django
import json

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_backend.settings')
django.setup()

from destinations.models import Destination, Attraction, Restaurant, Accommodation
from django.db.models import Count

# Path to JSON file
JSON_FILE_PATH = 'destinations_data.json'

def load_json_data():
    """Load destination data from JSON file"""
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ Error: {JSON_FILE_PATH} not found!")
        print(f"\nPlease create a JSON file named '{JSON_FILE_PATH}' in the same directory.")
        print("\nExpected JSON structure:")
        print(json.dumps({
            "destinations": [
                {
                    "name": "Goa",
                    "state": "Goa",
                    "country": "India",
                    "description": "Famous beaches...",
                    "geography_types": ["Coastal", "West India"],
                    "experience_types": ["Beach", "Relaxation"],
                    "landscape_types": ["Beaches"],
                    "spiritual_focus": [],
                    "budget_range_min": 20000,
                    "budget_range_max": 50000,
                    "typical_duration": 5,
                    "best_time_to_visit": ["November", "December"],
                    "avoid_months": ["June", "July"],
                    "difficulty_level": "easy",
                    "safety_rating": 4.7,
                    "popularity_score": 95.0,
                    "latitude": 15.2993,
                    "longitude": 74.1240,
                    "altitude": 10,
                    "climate_type": "Tropical",
                    "average_temperature_range": "20-32°C",
                    "nearest_airport": "Dabolim Airport",
                    "nearest_railway_station": "Madgaon",
                    "accessibility_features": [],
                    "is_active": True,
                    "is_verified": True,
                    "attractions": [
                        {
                            "name": "Baga Beach",
                            "type": "Beach",
                            "description": "Popular beach",
                            "rating": 4.5
                        }
                    ],
                    "restaurants": [
                        {
                            "name": "Fisherman's Wharf",
                            "cuisine": "Goan Seafood",
                            "rating": 4.4
                        }
                    ],
                    "accommodations": [
                        {
                            "name": "Taj Exotica",
                            "type": "Luxury Resort",
                            "rating": 4.8
                        }
                    ]
                }
            ]
        }, indent=2))
        sys.exit(1)
    
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'destinations' not in data:
            print("❌ Error: JSON must have a 'destinations' key with array of destinations")
            sys.exit(1)
        
        print(f"✓ Successfully loaded {len(data['destinations'])} destinations from JSON")
        return data['destinations']
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        sys.exit(1)


def populate_destinations(destinations_data):
    """Populate destinations from data"""
    print("\n" + "="*80)
    print("  DESTINATION POPULATION FROM JSON")
    print("="*80)
    
    created_count = 0
    updated_count = 0
    error_count = 0
    
    total_attractions = 0
    total_restaurants = 0
    total_accommodations = 0
    
    for dest_data in destinations_data:
        destination_name = dest_data.get('name', 'Unknown')
        
        try:
            # Extract nested data
            attractions_data = dest_data.pop('attractions', [])
            restaurants_data = dest_data.pop('restaurants', [])
            accommodations_data = dest_data.pop('accommodations', [])
            
            # Create or update destination
            destination, created = Destination.objects.update_or_create(
                name=destination_name,
                state=dest_data.get('state'),
                defaults=dest_data
            )
            
            if created:
                print(f"✓ Created: {destination.name:40} ({destination.state})")
                created_count += 1
            else:
                print(f"→ Updated: {destination.name:40} ({destination.state})")
                updated_count += 1
            
            # Create attractions
            for attr_data in attractions_data:
                Attraction.objects.get_or_create(
                    destination=destination,
                    name=attr_data['name'],
                    defaults={
                        'type': attr_data.get('type', 'Natural'),
                        'description': attr_data.get('description', ''),
                        'rating': attr_data.get('rating')
                    }
                )
                total_attractions += 1
            
            # Create restaurants
            for rest_data in restaurants_data:
                Restaurant.objects.get_or_create(
                    destination=destination,
                    name=rest_data['name'],
                    defaults={
                        'cuisine': rest_data.get('cuisine', 'Indian'),
                        'rating': rest_data.get('rating')
                    }
                )
                total_restaurants += 1
            
            # Create accommodations
            for acc_data in accommodations_data:
                Accommodation.objects.get_or_create(
                    destination=destination,
                    name=acc_data['name'],
                    defaults={
                        'type': acc_data.get('type', 'Hotel'),
                        'rating': acc_data.get('rating')
                    }
                )
                total_accommodations += 1
                
        except Exception as e:
            print(f"✗ Error with {destination_name}: {str(e)}")
            error_count += 1
    
    print("-"*80)
    print(f"\n📊 POPULATION SUMMARY:")
    print(f"  ✓ Destinations Created: {created_count}")
    print(f"  → Destinations Updated: {updated_count}")
    print(f"  ✗ Errors: {error_count}")
    print(f"  📍 Total Destinations: {Destination.objects.count()}")
    print(f"\n  🏛️  Attractions Added: {total_attractions}")
    print(f"  🍽️  Restaurants Added: {total_restaurants}")
    print(f"  🏨 Accommodations Added: {total_accommodations}")
    print("-"*80)


def show_statistics():
    """Show database statistics"""
    print("\n📈 DATABASE STATISTICS:")
    print("="*80)
    
    # By State
    print("\n🗺️  Top 10 States by Destinations:")
    stats = Destination.objects.values('state').annotate(count=Count('id')).order_by('-count')[:10]
    for stat in stats:
        print(f"  • {stat['state']:30} : {stat['count']:3} destinations")
    
    # By Geography
    print("\n🌍 By Geography Type:")
    geography_counts = {}
    for dest in Destination.objects.all():
        for geo in dest.geography_types:
            geography_counts[geo] = geography_counts.get(geo, 0) + 1
    for geo, count in sorted(geography_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  • {geo:30} : {count:3} destinations")
    
    # By Experience
    print("\n🎯 Top 10 Experience Types:")
    experience_counts = {}
    for dest in Destination.objects.all():
        for exp in dest.experience_types:
            experience_counts[exp] = experience_counts.get(exp, 0) + 1
    for exp, count in sorted(experience_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  • {exp:30} : {count:3} destinations")
    
    # By Difficulty
    print("\n⛰️  By Difficulty Level:")
    stats = Destination.objects.values('difficulty_level').annotate(count=Count('id'))
    for stat in stats:
        print(f"  • {stat['difficulty_level'].title():15} : {stat['count']:3} destinations")
    
    # By Budget Range
    print("\n💰 By Budget Range:")
    budget_ranges = [
        ("Budget (< ₹20k)", 0, 20000),
        ("Mid-Range (₹20k-40k)", 20000, 40000),
        ("Premium (₹40k-60k)", 40000, 60000),
        ("Luxury (> ₹60k)", 60000, 999999),
    ]
    for label, min_b, max_b in budget_ranges:
        count = Destination.objects.filter(
            budget_range_min__gte=min_b, 
            budget_range_max__lte=max_b
        ).count()
        print(f"  • {label:25} : {count:3} destinations")
    
    # Climate types
    print("\n🌡️  By Climate Type:")
    stats = Destination.objects.values('climate_type').annotate(count=Count('id')).order_by('-count')
    for stat in stats:
        print(f"  • {stat['climate_type']:15} : {stat['count']:3} destinations")
    
    print("="*80)


def main():
    """Main execution function"""
    print("\n" + "="*80)
    print("  COMPREHENSIVE DESTINATION POPULATION SCRIPT")
    print("="*80)
    print(f"\nLooking for JSON file: {JSON_FILE_PATH}")
    
    # Load data from JSON
    destinations_data = load_json_data()
    
    # Populate database
    populate_destinations(destinations_data)
    
    # Show statistics
    show_statistics()
    
    print("\n✅ POPULATION COMPLETE!")
    print("\n📝 Next Steps:")
    print("  1. Start server: python manage.py runserver")
    print("  2. Test search: python search_examples.py")
    print("  3. Run API tests: python test_api.py")
    print("  4. Admin panel: http://localhost:8000/admin/")
    print("\n")


if __name__ == '__main__':
    main()