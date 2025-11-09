from rest_framework import serializers
from .models import Itinerary, DayPlan, Activity, Transportation, ItineraryShare
from recommendations.serializers import DestinationListSerializer, AttractionSerializer, RestaurantSerializer, AccommodationSerializer
from datetime import datetime, timedelta


class ActivitySerializer(serializers.ModelSerializer):
    attraction_details = AttractionSerializer(source='attraction', read_only=True)
    restaurant_details = RestaurantSerializer(source='restaurant', read_only=True)
    accommodation_details = AccommodationSerializer(source='accommodation', read_only=True)
    
    class Meta:
        model = Activity
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DayPlanSerializer(serializers.ModelSerializer):
    activities = ActivitySerializer(many=True, read_only=True)
    
    class Meta:
        model = DayPlan
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class TransportationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transportation
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ItineraryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    destination_name = serializers.CharField(source='destination.name', read_only=True)
    destination_state = serializers.CharField(source='destination.state', read_only=True)
    days_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Itinerary
        fields = [
            'id', 'title', 'description', 'destination', 'destination_name', 'destination_state',
            'start_date', 'end_date', 'duration_days', 'days_count', 'number_of_travelers',
            'companion_type', 'total_budget', 'budget_per_person', 'status', 'is_public',
            'views_count', 'likes_count', 'created_at', 'updated_at'
        ]
    
    def get_days_count(self, obj):
        return obj.day_plans.count()


class ItineraryDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with all related data"""
    destination_details = DestinationListSerializer(source='destination', read_only=True)
    day_plans = DayPlanSerializer(many=True, read_only=True)
    transportations = TransportationSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Itinerary
        fields = '__all__'
        read_only_fields = ['id', 'user', 'views_count', 'likes_count', 'created_at', 'updated_at']


class ItineraryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Itinerary
        fields = [
            'title', 'description', 'destination', 'start_date', 'end_date',
            'number_of_travelers', 'companion_type', 'total_budget', 'currency',
            'pace', 'interests', 'is_public'
        ]
    
    def validate(self, data):
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError("End date must be after start date")
        
        if data['total_budget'] < 0:
            raise serializers.ValidationError("Budget cannot be negative")
        
        if data['number_of_travelers'] < 1:
            raise serializers.ValidationError("Number of travelers must be at least 1")
        
        return data
    
    def create(self, validated_data):
        # Calculate duration
        duration = (validated_data['end_date'] - validated_data['start_date']).days + 1
        validated_data['duration_days'] = duration
        
        # Calculate per person budget
        validated_data['budget_per_person'] = validated_data['total_budget'] / validated_data['number_of_travelers']
        
        # Set user from context
        validated_data['user'] = self.context['request'].user
        
        # Create itinerary first
        itinerary = Itinerary.objects.create(**validated_data)
        
        # Auto-create day plans after itinerary is created
        try:
            from .itinerary_generator import ItineraryGenerator
            generator = ItineraryGenerator()
            generator.create_day_plans(itinerary)
        except Exception as e:
            # If auto-generation fails, still return the itinerary
            # User can manually add day plans
            pass
        
        return itinerary
    
    def to_representation(self, instance):
        """Return detailed representation after creation"""
        return ItineraryDetailSerializer(instance, context=self.context).data


class ActivityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            'day_plan', 'title', 'description', 'activity_type',
            'attraction', 'restaurant', 'accommodation',
            'start_time', 'end_time', 'location_name',
            'latitude', 'longitude', 'address', 'estimated_cost', 'notes'
        ]
    
    def validate(self, data):
        if data['end_time'] <= data['start_time']:
            raise serializers.ValidationError("End time must be after start time")
        
        # Calculate duration
        start = datetime.combine(datetime.today(), data['start_time'])
        end = datetime.combine(datetime.today(), data['end_time'])
        duration = (end - start).seconds // 60
        data['duration_minutes'] = duration
        
        return data


class ItineraryShareSerializer(serializers.ModelSerializer):
    itinerary_title = serializers.CharField(source='itinerary.title', read_only=True)
    shared_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ItineraryShare
        fields = '__all__'
        read_only_fields = ['id', 'share_token', 'created_at']
    
    def get_shared_by_name(self, obj):
        return obj.shared_by.get_full_name() or obj.shared_by.email