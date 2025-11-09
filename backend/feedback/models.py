from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from users.models import User
from destinations.models import Destination


class DestinationReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='reviews')
    
    # Rating (1-5)
    overall_rating = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(5.0)])
    cleanliness_rating = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(5.0)], null=True, blank=True)
    safety_rating = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(5.0)], null=True, blank=True)
    value_for_money_rating = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(5.0)], null=True, blank=True)
    accessibility_rating = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(5.0)], null=True, blank=True)
    
    # Review content
    title = models.CharField(max_length=255)
    review_text = models.TextField()
    
    # Visit details
    visit_date = models.DateField(null=True, blank=True)
    trip_type = models.CharField(max_length=50, blank=True)  # Solo, Family, Business, etc.
    
    # Media
    images = models.JSONField(default=list, blank=True)
    
    # Helpful votes
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)
    
    # Moderation
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    moderation_notes = models.TextField(blank=True)
    moderated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='moderated_reviews')
    moderated_at = models.DateTimeField(null=True, blank=True)
    
    # Fraud detection
    is_verified_visit = models.BooleanField(default=False)
    anomaly_score = models.FloatField(default=0.0)
    
    # Sentiment analysis
    sentiment_score = models.FloatField(null=True, blank=True)  # -1 to 1
    sentiment_label = models.CharField(max_length=20, blank=True)  # positive, negative, neutral
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'destination_reviews'
        verbose_name = 'Destination Review'
        verbose_name_plural = 'Destination Reviews'
        ordering = ['-created_at']
        unique_together = ['user', 'destination']
        indexes = [
            models.Index(fields=['destination', 'status']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.destination.name} ({self.overall_rating}★)"


class ReviewHelpful(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(DestinationReview, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='helpful_votes')
    
    is_helpful = models.BooleanField()  # True = helpful, False = not helpful
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'review_helpful_votes'
        verbose_name = 'Review Helpful Vote'
        verbose_name_plural = 'Review Helpful Votes'
        unique_together = ['review', 'user']
    
    def __str__(self):
        return f"{self.user.email} - {'Helpful' if self.is_helpful else 'Not Helpful'}"


class ReviewFlag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(DestinationReview, on_delete=models.CASCADE, related_name='flags')
    flagged_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flagged_reviews')
    
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('offensive', 'Offensive Content'),
        ('fake', 'Fake Review'),
        ('irrelevant', 'Irrelevant'),
        ('duplicate', 'Duplicate'),
        ('other', 'Other'),
    ]
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('action_taken', 'Action Taken'),
        ('dismissed', 'Dismissed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_flags')
    
    class Meta:
        db_table = 'review_flags'
        verbose_name = 'Review Flag'
        verbose_name_plural = 'Review Flags'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Flag: {self.review.id} - {self.reason}"


class UserFeedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback')
    
    CATEGORY_CHOICES = [
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('recommendation_quality', 'Recommendation Quality'),
        ('ui_ux', 'UI/UX'),
        ('performance', 'Performance'),
        ('general', 'General Feedback'),
    ]
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    
    subject = models.CharField(max_length=255)
    message = models.TextField()
    
    # Rating
    app_rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    
    # Attachments
    attachments = models.JSONField(default=list, blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Admin response
    admin_response = models.TextField(blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedback_responses')
    responded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_feedback'
        verbose_name = 'User Feedback'
        verbose_name_plural = 'User Feedback'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.category} - {self.subject}"


class NPSScore(models.Model):
    """Net Promoter Score tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nps_scores')
    
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    feedback = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'nps_scores'
        verbose_name = 'NPS Score'
        verbose_name_plural = 'NPS Scores'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.score}/10"
    
    @property
    def category(self):
        if self.score >= 9:
            return 'Promoter'
        elif self.score >= 7:
            return 'Passive'
        else:
            return 'Detractor'