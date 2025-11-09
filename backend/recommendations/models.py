from django.db import models
import uuid
from users.models import User
from destinations.models import Destination


class UserRecommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE)
    
    # Recommendation metadata
    recommendation_score = models.FloatField()
    recommendation_reason = models.JSONField(default=dict)
    algorithm_used = models.CharField(max_length=100)
    
    # User interaction
    is_clicked = models.BooleanField(default=False)
    is_bookmarked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Context
    context = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_recommendations'
        verbose_name = 'User Recommendation'
        verbose_name_plural = 'User Recommendations'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['destination']),
        ]
    
    def __str__(self):
        return f"Recommendation for {self.user.email} - {self.destination.name}"


class UserBookmark(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE)
    
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_bookmarks'
        verbose_name = 'User Bookmark'
        verbose_name_plural = 'User Bookmarks'
        unique_together = ['user', 'destination']
    
    def __str__(self):
        return f"{self.user.email} - {self.destination.name}"


class TravelAdvisory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='advisories', 
                                   null=True, blank=True)
    state = models.CharField(max_length=100, blank=True)
    
    advisory_type = models.CharField(max_length=50)  # Weather, Safety, Health, Political
    severity = models.CharField(max_length=20, 
                               choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')])
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    
    source = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'travel_advisories'
        verbose_name = 'Travel Advisory'
        verbose_name_plural = 'Travel Advisories'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.advisory_type} - {self.title}"