from django.db import models
import uuid


class Destination(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('moderate', 'Moderate'),
        ('difficult', 'Difficult'),
    ]
    
    CLIMATE_CHOICES = [
        ('Tropical', 'Tropical'),
        ('Subtropical', 'Subtropical'),
        ('Temperate', 'Temperate'),
        ('Alpine', 'Alpine'),
        ('Arid', 'Arid'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=255, unique=True, db_index=True)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    description = models.TextField()
    
    # Classification
    geography_types = models.JSONField(default=list, blank=True)
    experience_types = models.JSONField(default=list, blank=True)
    landscape_types = models.JSONField(default=list, blank=True)
    spiritual_focus = models.JSONField(default=list, blank=True)
    
    # Budget & Planning
    budget_range_min = models.IntegerField(help_text="Minimum budget in INR")
    budget_range_max = models.IntegerField(help_text="Maximum budget in INR")
    typical_duration = models.IntegerField(help_text="Typical trip duration in days")
    
    # Timing
    best_time_to_visit = models.JSONField(default=list, blank=True)
    avoid_months = models.JSONField(default=list, blank=True)
    
    # Ratings & Difficulty
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    safety_rating = models.FloatField(default=0.0)
    popularity_score = models.FloatField(default=0.0)
    
    # Location Data
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude = models.IntegerField(help_text="Altitude in meters")
    
    # Climate
    climate_type = models.CharField(max_length=50, choices=CLIMATE_CHOICES)
    average_temperature_range = models.CharField(max_length=50)
    
    # Accessibility
    nearest_airport = models.CharField(max_length=255)
    nearest_railway_station = models.CharField(max_length=255)
    accessibility_features = models.JSONField(default=list, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'destinations'
        verbose_name = 'Destination'
        verbose_name_plural = 'Destinations'
        ordering = ['-popularity_score', 'name']
        indexes = [
            models.Index(fields=['name', 'is_active']),
            models.Index(fields=['state', 'country']),
            models.Index(fields=['popularity_score']),
        ]
    
    def __str__(self):
        return f"{self.name}, {self.state}"
    
    def get_budget_range(self):
        """Return formatted budget range"""
        return f"₹{self.budget_range_min:,} - ₹{self.budget_range_max:,}"
    
    def is_suitable_for_month(self, month):
        """Check if destination is suitable for given month"""
        if month in self.avoid_months:
            return False
        return month in self.best_time_to_visit
    
    def matches_budget(self, user_budget):
        """Check if destination matches user budget"""
        return self.budget_range_min <= user_budget <= self.budget_range_max


class Attraction(models.Model):
    """Attractions and points of interest at destinations"""
    ATTRACTION_TYPES = [
        ('Beach', 'Beach'),
        ('Historical', 'Historical'),
        ('Spiritual/Historical', 'Spiritual/Historical'),
        ('Spiritual', 'Spiritual'),
        ('Natural', 'Natural'),
        ('Adventure', 'Adventure'),
        ('Cultural', 'Cultural'),
        ('Wildlife', 'Wildlife'),
        ('Museum', 'Museum'),
        ('Monument', 'Monument'),
        ('Park', 'Park'),
        ('Temple', 'Temple'),
        ('Fort', 'Fort'),
        ('Lake', 'Lake'),
        ('Waterfall', 'Waterfall'),
        ('ViewPoint', 'View Point'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destination = models.ForeignKey(
        Destination, 
        on_delete=models.CASCADE, 
        related_name='destination_attractions'
    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=ATTRACTION_TYPES)
    description = models.TextField()
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attractions'
        verbose_name = 'Attraction'
        verbose_name_plural = 'Attractions'
        ordering = ['-rating', 'name']
        indexes = [
            models.Index(fields=['destination', 'type']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.destination.name}"


class Restaurant(models.Model):
    """Restaurants and dining options at destinations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destination = models.ForeignKey(
        Destination, 
        on_delete=models.CASCADE, 
        related_name='destination_restaurants'
    )
    name = models.CharField(max_length=255)
    cuisine = models.CharField(max_length=100)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'restaurants'
        verbose_name = 'Restaurant'
        verbose_name_plural = 'Restaurants'
        ordering = ['-rating', 'name']
        indexes = [
            models.Index(fields=['destination', 'cuisine']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.cuisine}) - {self.destination.name}"


class Accommodation(models.Model):
    """Accommodation options at destinations"""
    ACCOMMODATION_TYPES = [
        ('Luxury Resort', 'Luxury Resort'),
        ('Boutique/Luxury', 'Boutique/Luxury'),
        ('Hotel', 'Hotel'),
        ('Budget Hotel', 'Budget Hotel'),
        ('Homestay', 'Homestay'),
        ('Guest House', 'Guest House'),
        ('Hostel', 'Hostel'),
        ('Villa', 'Villa'),
        ('Cottage', 'Cottage'),
        ('Camp', 'Camp'),
        ('Lodge', 'Lodge'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destination = models.ForeignKey(
        Destination, 
        on_delete=models.CASCADE, 
        related_name='destination_accommodations'
    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=ACCOMMODATION_TYPES)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accommodations'
        verbose_name = 'Accommodation'
        verbose_name_plural = 'Accommodations'
        ordering = ['-rating', 'name']
        indexes = [
            models.Index(fields=['destination', 'type']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.type}) - {self.destination.name}"


class DestinationTag(models.Model):
    """Tags for better search and filtering"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='tags')
    tag_name = models.CharField(max_length=100)
    tag_category = models.CharField(max_length=50)  # activity, vibe, feature, etc.
    
    class Meta:
        db_table = 'destination_tags'
        unique_together = ['destination', 'tag_name']
        indexes = [
            models.Index(fields=['tag_name']),
        ]
    
    def __str__(self):
        return f"{self.destination.name} - {self.tag_name}"


class UserDestinationInteraction(models.Model):
    """Track user interactions with destinations"""
    INTERACTION_TYPES = [
        ('viewed', 'Viewed'),
        ('saved', 'Saved'),
        ('shared', 'Shared'),
        ('booked', 'Booked'),
        ('reviewed', 'Reviewed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_destination_interactions'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['destination', 'interaction_type']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.interaction_type} - {self.destination.name}"