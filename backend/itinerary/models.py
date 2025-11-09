from django.db import models
import uuid
from users.models import User
from destinations.models import Destination, Attraction, Restaurant, Accommodation
from recommendations.models import TravelAdvisory


class Itinerary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='itineraries')
    
    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='itineraries')
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.IntegerField()
    
    # Travel details
    number_of_travelers = models.IntegerField(default=1)
    companion_type = models.CharField(max_length=50, blank=True)  # Solo, Family, Friends, Couple
    
    # Budget
    total_budget = models.FloatField()
    budget_per_person = models.FloatField()
    currency = models.CharField(max_length=10, default='INR')
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Preferences
    pace = models.CharField(max_length=20, default='moderate')  # relaxed, moderate, fast
    interests = models.JSONField(default=list, blank=True)
    
    # Metadata
    is_public = models.BooleanField(default=False)
    views_count = models.IntegerField(default=0)
    likes_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'itineraries'
        verbose_name = 'Itinerary'
        verbose_name_plural = 'Itineraries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['destination']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.destination.name}"


class DayPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name='day_plans')
    
    day_number = models.IntegerField()
    date = models.DateField()
    title = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    
    # Budget for this day
    estimated_cost = models.FloatField(default=0.0)
    actual_cost = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'day_plans'
        verbose_name = 'Day Plan'
        verbose_name_plural = 'Day Plans'
        ordering = ['day_number']
        unique_together = ['itinerary', 'day_number']
    
    def __str__(self):
        return f"Day {self.day_number} - {self.itinerary.title}"


class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    day_plan = models.ForeignKey(DayPlan, on_delete=models.CASCADE, related_name='activities')
    
    # Activity details
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    ACTIVITY_TYPES = [
        ('attraction', 'Attraction Visit'),
        ('meal', 'Meal'),
        ('transport', 'Transportation'),
        ('accommodation', 'Accommodation'),
        ('free_time', 'Free Time'),
        ('shopping', 'Shopping'),
        ('other', 'Other'),
    ]
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    
    # Related objects (optional)
    attraction = models.ForeignKey(Attraction, on_delete=models.SET_NULL, null=True, blank=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True, blank=True)
    accommodation = models.ForeignKey(Accommodation, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timing
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.IntegerField()
    
    # Location
    location_name = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    address = models.TextField(blank=True)
    
    # Cost
    estimated_cost = models.FloatField(default=0.0)
    actual_cost = models.FloatField(null=True, blank=True)
    
    # Order in the day
    order = models.IntegerField(default=0)
    
    # Status
    is_completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'activities'
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'
        ordering = ['order', 'start_time']
    
    def __str__(self):
        return f"{self.title} - {self.start_time}"


class Transportation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name='transportations')
    
    TRANSPORT_TYPES = [
        ('flight', 'Flight'),
        ('train', 'Train'),
        ('bus', 'Bus'),
        ('car', 'Car/Taxi'),
        ('bike', 'Bike/Scooter'),
        ('auto', 'Auto-rickshaw'),
        ('metro', 'Metro'),
        ('ferry', 'Ferry'),
        ('walk', 'Walking'),
        ('other', 'Other'),
    ]
    transport_type = models.CharField(max_length=20, choices=TRANSPORT_TYPES)
    
    # Route
    from_location = models.CharField(max_length=255)
    to_location = models.CharField(max_length=255)
    
    # Timing
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    duration_minutes = models.IntegerField()
    
    # Details
    booking_reference = models.CharField(max_length=100, blank=True)
    seat_number = models.CharField(max_length=50, blank=True)
    carrier_name = models.CharField(max_length=255, blank=True)  # Airline, Train name, etc.
    
    # Cost
    cost = models.FloatField()
    booking_status = models.CharField(max_length=20, default='planned')  # planned, booked, completed
    
    # Carbon footprint (optional)
    carbon_footprint_kg = models.FloatField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transportations'
        verbose_name = 'Transportation'
        verbose_name_plural = 'Transportations'
        ordering = ['departure_time']
    
    def __str__(self):
        return f"{self.transport_type}: {self.from_location} → {self.to_location}"


class ItineraryShare(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_itineraries')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_itineraries', null=True, blank=True)
    
    # Share settings
    share_token = models.CharField(max_length=100, unique=True)
    is_public_link = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'itinerary_shares'
        verbose_name = 'Itinerary Share'
        verbose_name_plural = 'Itinerary Shares'
    
    def __str__(self):
        return f"Share: {self.itinerary.title}"