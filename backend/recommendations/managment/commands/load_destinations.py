from django.core.management.base import BaseCommand
from destinations.models import Destination, Attraction, Restaurant, Accommodation
from recommendations.models import TravelAdvisory
import random


class Command(BaseCommand):
    help = 'Load sample Indian destinations into database'
    
    def handle(self, *args, **kwargs):
        self.stdout.write('Loading sample destinations...')
        
        destinations_data = [
            {
                'name': 'Manali',
                'state': 'Himachal Pradesh',
                'description': 'A beautiful hill station nestled in the Himalayas, known for adventure sports, snow-capped mountains, and scenic beauty.',
                'latitude': 32.2396,
                'longitude': 77.1887,
                'altitude': 2050,
                'geography_types': ['Himalayan', 'North India'],
                'experience_types': ['Adventure', 'Relaxation', 'Mountain', 'Trekking'],
                'landscape_types': ['Mountains', 'Valleys'],
                'best_time_to_visit': ['May', 'June', 'September', 'October'],
                'avoid_months': ['January', 'February'],
                'typical_duration': 4,
                'budget_range_min': 2000,
                'budget_range_max': 8000,
                'climate_type': 'Alpine',
                'average_temperature_range': '5-20°C',
                'difficulty_level': 'moderate',
                'popularity_score': 85.0,
                'safety_rating': 4.5,
                'nearest_airport': 'Kullu-Manali Airport',
                'nearest_railway_station': 'Joginder Nagar',
            },
            {
                'name': 'Goa',
                'state': 'Goa',
                'description': 'Famous for its pristine beaches, Portuguese heritage, vibrant nightlife, and seafood. Perfect beach destination.',
                'latitude': 15.2993,
                'longitude': 74.1240,
                'altitude': 10,
                'geography_types': ['Coastal', 'West India'],
                'experience_types': ['Beach', 'Relaxation', 'Food & Culinary', 'Water Sports'],
                'landscape_types': ['Beaches', 'Islands'],
                'best_time_to_visit': ['November', 'December', 'January', 'February'],
                'avoid_months': ['June', 'July', 'August'],
                'typical_duration': 5,
                'budget_range_min': 1500,
                'budget_range_max': 6000,
                'climate_type': 'Tropical',
                'average_temperature_range': '20-32°C',
                'difficulty_level': 'easy',
                'popularity_score': 95.0,
                'safety_rating': 4.7,
                'nearest_airport': 'Dabolim Airport',
                'nearest_railway_station': 'Madgaon',
            },
            {
                'name': 'Jaipur',
                'state': 'Rajasthan',
                'description': 'The Pink City, known for magnificent forts, palaces, vibrant culture, and traditional Rajasthani cuisine.',
                'latitude': 26.9124,
                'longitude': 75.7873,
                'altitude': 431,
                'geography_types': ['North India', 'Desert'],
                'experience_types': ['Cultural', 'Historical', 'Food & Culinary', 'Shopping'],
                'landscape_types': ['Hills'],
                'spiritual_focus': ['Hindu Temples'],
                'best_time_to_visit': ['October', 'November', 'December', 'January', 'February', 'March'],
                'avoid_months': ['May', 'June'],
                'typical_duration': 3,
                'budget_range_min': 1000,
                'budget_range_max': 5000,
                'climate_type': 'Arid',
                'average_temperature_range': '15-40°C',
                'difficulty_level': 'easy',
                'popularity_score': 88.0,
                'safety_rating': 4.6,
                'nearest_airport': 'Jaipur International Airport',
                'nearest_railway_station': 'Jaipur Junction',
            },
            {
                'name': 'Kerala Backwaters',
                'state': 'Kerala',
                'description': 'Serene network of lagoons and lakes, famous for houseboat cruises, lush greenery, and Ayurvedic treatments.',
                'latitude': 9.4981,
                'longitude': 76.3388,
                'altitude': 5,
                'geography_types': ['Coastal', 'South India'],
                'experience_types': ['Relaxation', 'Wellness', 'Cultural', 'Food & Culinary'],
                'landscape_types': ['Lakes', 'Rivers', 'Beaches'],
                'best_time_to_visit': ['September', 'October', 'November', 'December', 'January', 'February', 'March'],
                'avoid_months': ['May', 'June'],
                'typical_duration': 4,
                'budget_range_min': 2500,
                'budget_range_max': 10000,
                'climate_type': 'Tropical',
                'average_temperature_range': '22-32°C',
                'difficulty_level': 'easy',
                'popularity_score': 82.0,
                'safety_rating': 4.8,
                'nearest_airport': 'Cochin International Airport',
                'nearest_railway_station': 'Alappuzha',
            },
            {
                'name': 'Ladakh',
                'state': 'Ladakh',
                'description': 'Land of high passes, featuring stunning landscapes, Buddhist monasteries, and adventure opportunities.',
                'latitude': 34.1526,
                'longitude': 77.5771,
                'altitude': 3500,
                'geography_types': ['Himalayan', 'North India'],
                'experience_types': ['Adventure', 'Mountain', 'Trekking', 'Photography'],
                'landscape_types': ['Mountains', 'Valleys', 'Deserts'],
                'spiritual_focus': ['Buddhist Monasteries'],
                'best_time_to_visit': ['June', 'July', 'August', 'September'],
                'avoid_months': ['November', 'December', 'January', 'February', 'March'],
                'typical_duration': 7,
                'budget_range_min': 3000,
                'budget_range_max': 12000,
                'climate_type': 'Alpine',
                'average_temperature_range': '-5-15°C',
                'difficulty_level': 'hard',
                'popularity_score': 90.0,
                'safety_rating': 4.3,
                'nearest_airport': 'Kushok Bakula Rimpochee Airport',
                'nearest_railway_station': 'Jammu Tawi',
            },
            {
                'name': 'Udaipur',
                'state': 'Rajasthan',
                'description': 'The City of Lakes, known for romantic settings, grand palaces, and rich cultural heritage.',
                'latitude': 24.5854,
                'longitude': 73.7125,
                'altitude': 577,
                'geography_types': ['North India', 'Desert'],
                'experience_types': ['Cultural', 'Relaxation', 'Historical', 'Honeymoon'],
                'landscape_types': ['Lakes', 'Hills'],
                'spiritual_focus': ['Hindu Temples'],
                'best_time_to_visit': ['September', 'October', 'November', 'December', 'January', 'February', 'March'],
                'avoid_months': ['May', 'June', 'July'],
                'typical_duration': 3,
                'budget_range_min': 1500,
                'budget_range_max': 7000,
                'climate_type': 'Arid',
                'average_temperature_range': '12-38°C',
                'difficulty_level': 'easy',
                'popularity_score': 87.0,
                'safety_rating': 4.7,
                'nearest_airport': 'Maharana Pratap Airport',
                'nearest_railway_station': 'Udaipur City',
            },
            {
                'name': 'Rishikesh',
                'state': 'Uttarakhand',
                'description': 'Yoga capital of the world, situated on Ganges riverbanks, known for spirituality and adventure sports.',
                'latitude': 30.0869,
                'longitude': 78.2676,
                'altitude': 372,
                'geography_types': ['Himalayan', 'North India'],
                'experience_types': ['Spiritual', 'Adventure', 'Wellness', 'Trekking'],
                'landscape_types': ['Mountains', 'Rivers'],
                'spiritual_focus': ['Hindu Temples', 'Meditation Centers'],
                'best_time_to_visit': ['September', 'October', 'November', 'February', 'March', 'April', 'May'],
                'avoid_months': ['July', 'August'],
                'typical_duration': 3,
                'budget_range_min': 1000,
                'budget_range_max': 4000,
                'climate_type': 'Temperate',
                'average_temperature_range': '10-35°C',
                'difficulty_level': 'moderate',
                'popularity_score': 83.0,
                'safety_rating': 4.6,
                'nearest_airport': 'Jolly Grant Airport',
                'nearest_railway_station': 'Rishikesh',
            },
            {
                'name': 'Darjeeling',
                'state': 'West Bengal',
                'description': 'Queen of the Hills, famous for tea gardens, toy train, and stunning views of Kanchenjunga.',
                'latitude': 27.0360,
                'longitude': 88.2627,
                'altitude': 2045,
                'geography_types': ['Himalayan', 'East India'],
                'experience_types': ['Relaxation', 'Cultural', 'Photography', 'Mountain'],
                'landscape_types': ['Mountains', 'Valleys'],
                'best_time_to_visit': ['March', 'April', 'May', 'October', 'November'],
                'avoid_months': ['June', 'July', 'August'],
                'typical_duration': 4,
                'budget_range_min': 1500,
                'budget_range_max': 5000,
                'climate_type': 'Temperate',
                'average_temperature_range': '5-15°C',
                'difficulty_level': 'easy',
                'popularity_score': 81.0,
                'safety_rating': 4.5,
                'nearest_airport': 'Bagdogra Airport',
                'nearest_railway_station': 'New Jalpaiguri',
            },
            {
                'name': 'Varanasi',
                'state': 'Uttar Pradesh',
                'description': 'One of the oldest cities in the world, spiritual capital of India, known for ghats and Ganga Aarti.',
                'latitude': 25.3176,
                'longitude': 82.9739,
                'altitude': 80,
                'geography_types': ['North India', 'Central India'],
                'experience_types': ['Spiritual', 'Cultural', 'Historical', 'Pilgrimage'],
                'landscape_types': ['Rivers'],
                'spiritual_focus': ['Shiva Temples', 'Hindu Temples'],
                'best_time_to_visit': ['October', 'November', 'December', 'January', 'February', 'March'],
                'avoid_months': ['May', 'June', 'July'],
                'typical_duration': 2,
                'budget_range_min': 800,
                'budget_range_max': 3000,
                'climate_type': 'Subtropical',
                'average_temperature_range': '10-45°C',
                'difficulty_level': 'easy',
                'popularity_score': 86.0,
                'safety_rating': 4.4,
                'nearest_airport': 'Lal Bahadur Shastri Airport',
                'nearest_railway_station': 'Varanasi Junction',
            },
            {
                'name': 'Andaman Islands',
                'state': 'Andaman and Nicobar Islands',
                'description': 'Tropical paradise with crystal clear waters, coral reefs, and pristine beaches perfect for water sports.',
                'latitude': 11.7401,
                'longitude': 92.6586,
                'altitude': 5,
                'geography_types': ['Coastal', 'Islands'],
                'experience_types': ['Beach', 'Water Sports', 'Relaxation', 'Honeymoon'],
                'landscape_types': ['Islands', 'Beaches'],
                'best_time_to_visit': ['October', 'November', 'December', 'January', 'February', 'March', 'April', 'May'],
                'avoid_months': ['June', 'July', 'August', 'September'],
                'typical_duration': 6,
                'budget_range_min': 4000,
                'budget_range_max': 15000,
                'climate_type': 'Tropical',
                'average_temperature_range': '23-31°C',
                'difficulty_level': 'easy',
                'popularity_score': 89.0,
                'safety_rating': 4.7,
                'nearest_airport': 'Veer Savarkar International Airport',
                'nearest_railway_station': 'Chennai Central',
            },
        ]
        
        created_count = 0
        for dest_data in destinations_data:
            destination, created = Destination.objects.get_or_create(
                name=dest_data['name'],
                state=dest_data['state'],
                defaults=dest_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {destination.name}'))
                
                # Add sample attractions
                self._create_sample_attractions(destination)
                
                # Add sample restaurants
                self._create_sample_restaurants(destination)
                
                # Add sample accommodations
                self._create_sample_accommodations(destination)
            else:
                self.stdout.write(self.style.WARNING(f'- Already exists: {destination.name}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully created {created_count} destinations'))
    
    def _create_sample_attractions(self, destination):
        """Create sample attractions for a destination"""
        attractions_templates = {
            'Manali': [
                {'name': 'Solang Valley', 'category': 'Adventure Spot', 'duration': 4.0, 'fee': 0},
                {'name': 'Rohtang Pass', 'category': 'Mountain Pass', 'duration': 6.0, 'fee': 50},
                {'name': 'Hadimba Temple', 'category': 'Temple', 'duration': 1.5, 'fee': 0},
            ],
            'Goa': [
                {'name': 'Baga Beach', 'category': 'Beach', 'duration': 3.0, 'fee': 0},
                {'name': 'Fort Aguada', 'category': 'Historical Fort', 'duration': 2.0, 'fee': 25},
                {'name': 'Basilica of Bom Jesus', 'category': 'Church', 'duration': 1.5, 'fee': 0},
            ],
            'Jaipur': [
                {'name': 'Amber Fort', 'category': 'Fort', 'duration': 3.0, 'fee': 200},
                {'name': 'Hawa Mahal', 'category': 'Palace', 'duration': 1.0, 'fee': 50},
                {'name': 'City Palace', 'category': 'Palace', 'duration': 2.5, 'fee': 200},
            ],
        }
        
        templates = attractions_templates.get(destination.name, [
            {'name': f'{destination.name} Main Attraction', 'category': 'Landmark', 'duration': 2.0, 'fee': 50},
            {'name': f'{destination.name} Viewpoint', 'category': 'Scenic Spot', 'duration': 1.5, 'fee': 0},
        ])
        
        for template in templates:
            Attraction.objects.create(
                destination=destination,
                name=template['name'],
                description=f'Popular attraction in {destination.name}',
                category=template['category'],
                latitude=destination.latitude + random.uniform(-0.05, 0.05),
                longitude=destination.longitude + random.uniform(-0.05, 0.05),
                typical_visit_duration=template['duration'],
                entry_fee=template['fee'],
                rating=round(random.uniform(4.0, 5.0), 1),
                review_count=random.randint(50, 500)
            )
    
    def _create_sample_restaurants(self, destination):
        """Create sample restaurants for a destination"""
        cuisines_map = {
            'Goa': ['Goan', 'Seafood', 'Continental'],
            'Jaipur': ['Rajasthani', 'North Indian', 'Continental'],
            'Kerala Backwaters': ['Kerala', 'South Indian', 'Seafood'],
        }
        
        cuisines = cuisines_map.get(destination.name, ['Indian', 'Continental', 'Local'])
        
        restaurants = [
            {
                'name': f'{destination.name} Spice Garden',
                'cuisines': cuisines,
                'price_range': 'Mid-Range',
                'cost': random.randint(800, 1500)
            },
            {
                'name': f'Local Flavors - {destination.name}',
                'cuisines': cuisines[:2],
                'price_range': 'Budget',
                'cost': random.randint(400, 800)
            },
            {
                'name': f'Royal Dine {destination.name}',
                'cuisines': cuisines,
                'price_range': 'Expensive',
                'cost': random.randint(2000, 4000)
            },
        ]
        
        for rest_data in restaurants:
            Restaurant.objects.create(
                destination=destination,
                name=rest_data['name'],
                cuisine_types=rest_data['cuisines'],
                description=f'Popular restaurant serving {", ".join(rest_data["cuisines"])} cuisine',
                latitude=destination.latitude + random.uniform(-0.03, 0.03),
                longitude=destination.longitude + random.uniform(-0.03, 0.03),
                address=f'Main Market, {destination.name}, {destination.state}',
                price_range=rest_data['price_range'],
                average_cost_for_two=rest_data['cost'],
                rating=round(random.uniform(3.8, 4.8), 1),
                review_count=random.randint(100, 1000),
                dietary_options=['Vegetarian', 'Non-Vegetarian'],
                meal_types=['Lunch', 'Dinner']
            )
    
    def _create_sample_accommodations(self, destination):
        """Create sample accommodations for a destination"""
        accommodations = [
            {
                'name': f'{destination.name} Budget Stay',
                'type': 'Hostel',
                'price_min': 500,
                'price_max': 1200,
                'category': 'Budget'
            },
            {
                'name': f'{destination.name} Comfort Inn',
                'type': 'Hotel',
                'price_min': 2000,
                'price_max': 4000,
                'category': 'Mid-Range'
            },
            {
                'name': f'{destination.name} Luxury Resort',
                'type': 'Resort',
                'price_min': 8000,
                'price_max': 20000,
                'category': 'Luxury'
            },
        ]
        
        for acc_data in accommodations:
            Accommodation.objects.create(
                destination=destination,
                name=acc_data['name'],
                type=acc_data['type'],
                description=f'{acc_data["category"]} accommodation in {destination.name}',
                latitude=destination.latitude + random.uniform(-0.02, 0.02),
                longitude=destination.longitude + random.uniform(-0.02, 0.02),
                address=f'Tourist Area, {destination.name}, {destination.state}',
                price_range_min=acc_data['price_min'],
                price_range_max=acc_data['price_max'],
                budget_category=acc_data['category'],
                rating=round(random.uniform(3.5, 4.8), 1),
                review_count=random.randint(50, 500),
                amenities=['WiFi', 'Parking', 'Restaurant'],
                room_types=['Standard', 'Deluxe']
            )