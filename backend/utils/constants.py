# User Roles
USER_ROLES = {
    'USER': 'user',
    'ADMIN': 'admin',
    'MODERATOR': 'moderator',
}

# Geography Classifications
GEOGRAPHY_TYPES = [
    'North India', 'South India', 'East India', 'West India',
    'Himalayan', 'Coastal', 'Desert', 'Central India', 'Northeast India'
]

# Experience Types
EXPERIENCE_TYPES = [
    'Adventure', 'Relaxation', 'Wildlife', 'Pilgrimage', 'Cultural',
    'Food & Culinary', 'Historical', 'Shopping', 'Beach', 'Mountain',
    'Photography', 'Trekking', 'Water Sports', 'Spiritual', 'Wellness'
]

# Landscape Types
LANDSCAPE_TYPES = [
    'Beaches', 'Mountains', 'Forests', 'Islands', 'Deserts',
    'Lakes', 'Rivers', 'Valleys', 'Plateaus', 'Hills'
]

# Spiritual Focus
SPIRITUAL_FOCUS = [
    'Shiva Temples', 'Goddess Temples', 'Vishnu Temples',
    'Buddhist Monasteries', 'Jain Temples', 'Churches',
    'Mosques', 'Gurudwaras', 'Meditation Centers'
]

# Companion Types
COMPANION_TYPES = [
    'Solo', 'Couple', 'Family', 'Friends', 'Group',
    'Family with Kids', 'Family with Elderly', 'Honeymoon'
]

# Budget Ranges (in INR per person per day)
BUDGET_RANGES = {
    'Budget': (0, 2000),
    'Mid-Range': (2000, 5000),
    'Comfort': (5000, 10000),
    'Luxury': (10000, 25000),
    'Ultra-Luxury': (25000, float('inf'))
}

# Climate Preferences
CLIMATE_PREFERENCES = [
    'Tropical', 'Temperate', 'Cold', 'Dry', 'Humid',
    'Moderate', 'Hot', 'Pleasant'
]

# Accessibility Needs
ACCESSIBILITY_NEEDS = [
    'Wheelchair Accessible', 'Elderly Friendly', 'Child Friendly',
    'Pregnant Women Friendly', 'Limited Mobility Support',
    'Visual Impairment Support', 'Hearing Impairment Support'
]

# Transportation Modes
TRANSPORTATION_MODES = [
    'Flight', 'Train', 'Bus', 'Car/Taxi', 'Bike',
    'Auto-rickshaw', 'Metro', 'Ferry', 'Shared Cab',
    'Bicycle', 'Walking'
]

# Seasons
SEASONS = {
    'Winter': ['December', 'January', 'February'],
    'Spring': ['March', 'April'],
    'Summer': ['May', 'June'],
    'Monsoon': ['July', 'August', 'September'],
    'Autumn': ['October', 'November']
}

# Meal Types
MEAL_TYPES = ['Breakfast', 'Lunch', 'Dinner', 'Snacks']

# Activity Duration (in hours)
ACTIVITY_DURATIONS = {
    'Quick Visit': 1,
    'Short Visit': 2,
    'Half Day': 4,
    'Full Day': 8,
    'Multi-Day': 24
}

# Intent Types for Chatbot
INTENT_TYPES = [
    'greeting', 'destination_query', 'budget_query',
    'weather_query', 'itinerary_request', 'booking_help',
    'travel_dates', 'companion_info', 'preference_update',
    'feedback_submit', 'emergency_help', 'general_info',
    'goodbye'
]

# Entity Types for NER
ENTITY_TYPES = [
    'DESTINATION', 'DATE', 'DURATION', 'BUDGET', 'ACTIVITY',
    'ACCOMMODATION', 'TRANSPORT', 'CUISINE', 'LANDMARK',
    'PERSON_COUNT', 'COMPANION_TYPE'
]

# Feedback Categories
FEEDBACK_CATEGORIES = [
    'Recommendation Quality', 'Itinerary Accuracy', 'User Experience',
    'Response Time', 'Information Accuracy', 'Bug Report',
    'Feature Request', 'General Feedback'
]

# Rating Scale
RATING_SCALE = range(1, 6)  # 1 to 5

# Cache TTL (in seconds)
CACHE_TTL = {
    'weather': 1800,  # 30 minutes
    'destinations': 86400,  # 24 hours
    'recommendations': 3600,  # 1 hour
    'user_preferences': 7200,  # 2 hours
}

# API Rate Limits
RATE_LIMITS = {
    'chatbot': '100/hour',
    'recommendations': '50/hour',
    'itinerary': '30/hour',
    'feedback': '20/hour',
}

# Fraud Detection Thresholds
FRAUD_THRESHOLDS = {
    'min_rating_time': 5,  # seconds
    'max_daily_ratings': 20,
    'min_feedback_length': 10,  # characters
    'anomaly_score_threshold': 0.8,
}

# Recommendation Weights
RECOMMENDATION_WEIGHTS = {
    'user_preference': 0.4,
    'collaborative_filtering': 0.3,
    'content_similarity': 0.2,
    'popularity': 0.1,
}

# Default Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100