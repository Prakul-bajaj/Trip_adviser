from django.db import models
import uuid
from users.models import User


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, blank=True, default='')
    session_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Context tracking
    current_context = models.JSONField(default=dict, blank=True)
    extracted_info = models.JSONField(default=dict, blank=True)  # dates, budget, companions, etc.
    
    # Session metadata
    total_messages = models.IntegerField(default=0)
    language = models.CharField(max_length=10, default='en')
    
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_sessions'
        verbose_name = 'Chat Session'
        verbose_name_plural = 'Chat Sessions'
        ordering = ['-last_activity_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"Session {self.id} - {self.user.email}"


class Message(models.Model):
    SENDER_CHOICES = [
        ('user', 'User'),
        ('bot', 'Bot'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES, default='user')
    content = models.TextField()
    
    # NLP Analysis
    detected_intent = models.CharField(max_length=100, blank=True)
    detected_entities = models.JSONField(default=dict, blank=True)
    sentiment_score = models.FloatField(null=True, blank=True)
    sentiment_label = models.CharField(max_length=20, blank=True)
    
    # Language
    language = models.CharField(max_length=10, blank=True)
    translated_content = models.TextField(blank=True)
    
    # Bot response metadata
    response_time_ms = models.IntegerField(null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['session', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.sender_type}: {self.content[:50]}"


class ConversationState(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='state')
    
    current_flow = models.CharField(max_length=100, blank=True)
    current_step = models.CharField(max_length=100, blank=True)
    
    # Collected information
    travel_dates = models.JSONField(default=dict, blank=True)
    budget = models.JSONField(default=dict, blank=True)
    companions = models.JSONField(default=dict, blank=True)
    interests = models.JSONField(default=list, blank=True)
    last_intent = models.CharField(max_length=100, blank=True, null=True)
    extracted_info = models.JSONField(default=dict, blank=True)
    constraints = models.JSONField(default=list, blank=True)
    
    # ADD THIS NEW FIELD - Conversation memory/context
    context_data = models.JSONField(default=dict, blank=True, help_text="Stores conversation history and context")
    
    # Pending questions
    pending_questions = models.JSONField(default=list, blank=True)
    answered_questions = models.JSONField(default=list, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversation_states'
        verbose_name = 'Conversation State'
        verbose_name_plural = 'Conversation States'
    
    def __str__(self):
        return f"State for {self.session.id}"


class QuickReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    trigger_intent = models.CharField(max_length=100)
    context = models.CharField(max_length=100, blank=True)
    
    reply_text = models.CharField(max_length=100)
    reply_value = models.CharField(max_length=100)
    
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'quick_replies'
        verbose_name = 'Quick Reply'
        verbose_name_plural = 'Quick Replies'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.trigger_intent} - {self.reply_text}"