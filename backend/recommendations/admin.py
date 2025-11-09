from django.contrib import admin
from destinations.models import (
    Destination, Attraction, Restaurant, Accommodation, 
    DestinationTag, UserDestinationInteraction
)
from .models import UserRecommendation, UserBookmark, TravelAdvisory


class AttractionInline(admin.TabularInline):
    model = Attraction
    extra = 0
    fields = ['name', 'type', 'rating', 'description']


class RestaurantInline(admin.TabularInline):
    model = Restaurant
    extra = 0
    fields = ['name', 'cuisine', 'rating']


class AccommodationInline(admin.TabularInline):
    model = Accommodation
    extra = 0
    fields = ['name', 'type', 'rating']


class DestinationTagInline(admin.TabularInline):
    model = DestinationTag
    extra = 0
    fields = ['tag_name', 'tag_category']


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['name', 'state', 'country', 'popularity_score', 'safety_rating', 'is_active', 'is_verified']
    list_filter = ['state', 'country', 'difficulty_level', 'is_active', 'is_verified', 'climate_type']
    search_fields = ['name', 'state', 'description']
    inlines = [AttractionInline, RestaurantInline, AccommodationInline, DestinationTagInline]
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'state', 'country', 'is_active', 'is_verified')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'altitude')
        }),
        ('Classifications', {
            'fields': ('geography_types', 'experience_types', 'landscape_types', 'spiritual_focus')
        }),
        ('Travel Details', {
            'fields': ('best_time_to_visit', 'avoid_months', 'typical_duration', 
                      'budget_range_min', 'budget_range_max', 'difficulty_level')
        }),
        ('Accessibility', {
            'fields': ('nearest_airport', 'nearest_railway_station', 'accessibility_features')
        }),
        ('Climate', {
            'fields': ('climate_type', 'average_temperature_range')
        }),
        ('Metrics', {
            'fields': ('popularity_score', 'safety_rating')
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    list_display = ['name', 'destination', 'type', 'rating', 'created_at']
    list_filter = ['type', 'rating', 'destination']
    search_fields = ['name', 'description', 'destination__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'destination', 'cuisine', 'rating', 'created_at']
    list_filter = ['cuisine', 'rating', 'destination']
    search_fields = ['name', 'cuisine', 'destination__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Accommodation)
class AccommodationAdmin(admin.ModelAdmin):
    list_display = ['name', 'destination', 'type', 'rating', 'created_at']
    list_filter = ['type', 'rating', 'destination']
    search_fields = ['name', 'type', 'destination__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(DestinationTag)
class DestinationTagAdmin(admin.ModelAdmin):
    list_display = ['destination', 'tag_name', 'tag_category']
    list_filter = ['tag_category']
    search_fields = ['tag_name', 'destination__name']


@admin.register(UserDestinationInteraction)
class UserDestinationInteractionAdmin(admin.ModelAdmin):
    list_display = ['user', 'destination', 'interaction_type', 'timestamp']
    list_filter = ['interaction_type', 'timestamp']
    search_fields = ['user__email', 'user__username', 'destination__name']
    readonly_fields = ['id', 'timestamp']
    date_hierarchy = 'timestamp'


@admin.register(UserRecommendation)
class UserRecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'destination', 'recommendation_score', 'algorithm_used', 'is_clicked', 'is_bookmarked', 'created_at']
    list_filter = ['algorithm_used', 'is_clicked', 'is_bookmarked', 'created_at']
    search_fields = ['user__email', 'user__username', 'destination__name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Recommendation Details', {
            'fields': ('user', 'destination', 'recommendation_score', 'recommendation_reason', 'algorithm_used')
        }),
        ('User Interaction', {
            'fields': ('is_clicked', 'is_bookmarked', 'clicked_at')
        }),
        ('Context', {
            'fields': ('context',)
        }),
        ('System', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserBookmark)
class UserBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'destination', 'created_at', 'updated_at']
    search_fields = ['user__email', 'user__username', 'destination__name', 'notes']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Bookmark Details', {
            'fields': ('user', 'destination', 'notes', 'tags')
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TravelAdvisory)
class TravelAdvisoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'destination', 'state', 'advisory_type', 'severity', 'valid_from', 'valid_until', 'is_active']
    list_filter = ['advisory_type', 'severity', 'is_active', 'valid_from']
    search_fields = ['title', 'description', 'destination__name', 'state']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'valid_from'
    
    fieldsets = (
        ('Advisory Information', {
            'fields': ('destination', 'state', 'advisory_type', 'severity', 'title', 'description')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until', 'is_active')
        }),
        ('Source', {
            'fields': ('source', 'source_url')
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )