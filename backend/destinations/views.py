from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import Destination, Attraction, UserDestinationInteraction
from .serializers import (
    DestinationListSerializer, 
    DestinationDetailSerializer,
    SpiritualDestinationSerializer
)

class DestinationListView(generics.ListAPIView):
    """List all destinations with filtering and search"""
    queryset = Destination.objects.filter(is_active=True)
    serializer_class = DestinationListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'state': ['exact'],
        'country': ['exact'],
        'difficulty_level': ['exact'],
        'climate_type': ['exact'],
        'budget_range_min': ['gte', 'lte'],
        'budget_range_max': ['gte', 'lte'],
        'typical_duration': ['gte', 'lte'],
    }
    search_fields = ['name', 'description', 'state', 'spiritual_focus']
    ordering_fields = ['popularity_score', 'safety_rating', 'budget_range_min', 'name']
    ordering = ['-popularity_score']


class DestinationDetailView(generics.RetrieveAPIView):
    """Get detailed information about a destination"""
    queryset = Destination.objects.filter(is_active=True)
    serializer_class = DestinationDetailSerializer
    permission_classes = [AllowAny]
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Track user interaction if authenticated
        if request.user.is_authenticated:
            UserDestinationInteraction.objects.create(
                user=request.user,
                destination=instance,
                interaction_type='viewed'
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class SpiritualDestinationsView(generics.ListAPIView):
    """Get destinations with spiritual focus"""
    serializer_class = SpiritualDestinationSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['popularity_score', 'safety_rating', 'name']
    ordering = ['-popularity_score']
    
    def get_queryset(self):
        """Filter destinations that have spiritual focus"""
        # Get all active destinations
        all_destinations = Destination.objects.filter(is_active=True)
        
        # Filter in Python - collect IDs of destinations with spiritual_focus
        spiritual_ids = []
        for dest in all_destinations:
            if dest.spiritual_focus and len(dest.spiritual_focus) > 0:
                spiritual_ids.append(dest.id)
        
        # Return queryset filtered by these IDs
        return Destination.objects.filter(id__in=spiritual_ids)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_destinations_by_type(request, destination_type):
    """
    Get destinations filtered by type (geography, experience, landscape, spiritual)
    Example: /api/destinations/type/spiritual/buddhist/
    """
    type_param = request.GET.get('type', '').lower()
    
    # Build filter based on type
    queryset = Destination.objects.filter(is_active=True)
    
    if destination_type.lower() in ['spiritual', 'spirit']:
        # Filter by spiritual focus - need to do in Python for JSONField
        all_dests = list(queryset)
        filtered_ids = []
        for dest in all_dests:
            if dest.spiritual_focus and any(type_param in sf.lower() for sf in dest.spiritual_focus):
                filtered_ids.append(dest.id)
        queryset = Destination.objects.filter(id__in=filtered_ids)
    elif destination_type.lower() in ['geography', 'geo']:
        # Similar approach for consistency
        all_dests = list(queryset)
        filtered_ids = []
        for dest in all_dests:
            if dest.geography_types and any(type_param in gt.lower() for gt in dest.geography_types):
                filtered_ids.append(dest.id)
        queryset = Destination.objects.filter(id__in=filtered_ids)
    elif destination_type.lower() in ['experience', 'exp']:
        all_dests = list(queryset)
        filtered_ids = []
        for dest in all_dests:
            if dest.experience_types and any(type_param in et.lower() for et in dest.experience_types):
                filtered_ids.append(dest.id)
        queryset = Destination.objects.filter(id__in=filtered_ids)
    elif destination_type.lower() in ['landscape', 'land']:
        all_dests = list(queryset)
        filtered_ids = []
        for dest in all_dests:
            if dest.landscape_types and any(type_param in lt.lower() for lt in dest.landscape_types):
                filtered_ids.append(dest.id)
        queryset = Destination.objects.filter(id__in=filtered_ids)
    
    serializer = DestinationListSerializer(queryset, many=True)
    return Response({
        'count': queryset.count(),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def search_spiritual_places(request):
    """
    Search for spiritual places
    Query params:
    - q: search query
    - focus: specific spiritual focus (e.g., 'Hindu Temples', 'Buddhist Monasteries')
    - state: filter by state
    - budget_max: maximum budget
    - max_duration: maximum duration
    """
    # Get all active destinations first
    all_destinations = Destination.objects.filter(is_active=True)
    
    # Filter for spiritual destinations (Python-side)
    spiritual_ids = []
    for dest in all_destinations:
        if dest.spiritual_focus and len(dest.spiritual_focus) > 0:
            spiritual_ids.append(dest.id)
    
    queryset = Destination.objects.filter(id__in=spiritual_ids)
    
    # Search query
    search_query = request.GET.get('q', '')
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(state__icontains=search_query)
        )
    
    # Spiritual focus filter (need to filter in Python for JSONField contains)
    focus = request.GET.get('focus', '')
    if focus:
        filtered_ids = []
        for dest in queryset:
            if any(focus.lower() in sf.lower() for sf in dest.spiritual_focus):
                filtered_ids.append(dest.id)
        queryset = Destination.objects.filter(id__in=filtered_ids)
    
    # State filter
    state = request.GET.get('state', '')
    if state:
        queryset = queryset.filter(state__iexact=state)
    
    # Budget filter
    budget_max = request.GET.get('budget_max')
    if budget_max:
        try:
            queryset = queryset.filter(budget_range_max__lte=int(budget_max))
        except ValueError:
            pass
    
    # Duration filter
    max_duration = request.GET.get('max_duration')
    if max_duration:
        try:
            queryset = queryset.filter(typical_duration__lte=int(max_duration))
        except ValueError:
            pass
    
    # Order by popularity
    queryset = queryset.order_by('-popularity_score')
    
    serializer = SpiritualDestinationSerializer(queryset, many=True)
    return Response({
        'count': queryset.count(),
        'results': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_destination(request, destination_id):
    """Save/bookmark a destination"""
    try:
        destination = Destination.objects.get(id=destination_id, is_active=True)
        
        # Check if already saved
        interaction, created = UserDestinationInteraction.objects.get_or_create(
            user=request.user,
            destination=destination,
            interaction_type='saved'
        )
        
        if created:
            return Response({
                'message': 'Destination saved successfully',
                'saved': True
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'message': 'Destination already saved',
                'saved': True
            }, status=status.HTTP_200_OK)
            
    except Destination.DoesNotExist:
        return Response({
            'error': 'Destination not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unsave_destination(request, destination_id):
    """Remove a saved destination"""
    try:
        destination = Destination.objects.get(id=destination_id)
        UserDestinationInteraction.objects.filter(
            user=request.user,
            destination=destination,
            interaction_type='saved'
        ).delete()
        
        return Response({
            'message': 'Destination removed from saved list',
            'saved': False
        }, status=status.HTTP_200_OK)
        
    except Destination.DoesNotExist:
        return Response({
            'error': 'Destination not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_saved_destinations(request):
    """Get all saved destinations for the current user"""
    saved_interactions = UserDestinationInteraction.objects.filter(
        user=request.user,
        interaction_type='saved'
    ).select_related('destination')
    
    destinations = [interaction.destination for interaction in saved_interactions]
    serializer = DestinationListSerializer(destinations, many=True)
    
    return Response({
        'count': len(destinations),
        'results': serializer.data
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_destinations_by_experience(request, experience_type):
    """
    Get destinations by experience type (CASE-INSENSITIVE)
    """
    all_destinations = Destination.objects.filter(is_active=True)
    
    # Filter in Python for JSONField - CASE INSENSITIVE
    filtered_ids = []
    for dest in all_destinations:
        if dest.experience_types:
            # Check if any experience type matches (case-insensitive)
            for exp in dest.experience_types:
                if experience_type.lower() == exp.lower():
                    filtered_ids.append(dest.id)
                    break
    
    queryset = Destination.objects.filter(id__in=filtered_ids)
    
    # Apply additional filters
    state = request.GET.get('state')
    if state:
        queryset = queryset.filter(state__iexact=state)
    
    budget_max = request.GET.get('budget_max')
    if budget_max:
        try:
            queryset = queryset.filter(budget_range_max__lte=int(budget_max))
        except ValueError:
            pass
    
    queryset = queryset.order_by('-popularity_score')
    serializer = DestinationListSerializer(queryset, many=True)
    
    return Response({
        'category': experience_type,
        'count': queryset.count(),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_destinations_by_geography(request, geography_type):
    """
    Get destinations by geography type (CASE-INSENSITIVE)
    """
    all_destinations = Destination.objects.filter(is_active=True)
    
    # Filter in Python for JSONField - CASE INSENSITIVE
    filtered_ids = []
    for dest in all_destinations:
        if dest.geography_types:
            for geo in dest.geography_types:
                if geography_type.lower() == geo.lower():
                    filtered_ids.append(dest.id)
                    break
    
    queryset = Destination.objects.filter(id__in=filtered_ids)
    queryset = queryset.order_by('-popularity_score')
    serializer = DestinationListSerializer(queryset, many=True)
    
    return Response({
        'geography': geography_type,
        'count': queryset.count(),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_destinations_by_landscape(request, landscape_type):
    """
    Get destinations by landscape type (CASE-INSENSITIVE)
    """
    all_destinations = Destination.objects.filter(is_active=True)
    
    # Filter in Python for JSONField - CASE INSENSITIVE
    filtered_ids = []
    for dest in all_destinations:
        if dest.landscape_types:
            for land in dest.landscape_types:
                if landscape_type.lower() == land.lower():
                    filtered_ids.append(dest.id)
                    break
    
    queryset = Destination.objects.filter(id__in=filtered_ids)
    queryset = queryset.order_by('-popularity_score')
    serializer = DestinationListSerializer(queryset, many=True)
    
    return Response({
        'landscape': landscape_type,
        'count': queryset.count(),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_categories(request):
    """
    Get all available categories from the database
    """
    destinations = Destination.objects.filter(is_active=True)
    
    # Extract all unique categories
    experience_types = set()
    geography_types = set()
    landscape_types = set()
    spiritual_focus = set()
    
    for dest in destinations:
        experience_types.update(dest.experience_types)
        geography_types.update(dest.geography_types)
        landscape_types.update(dest.landscape_types)
        spiritual_focus.update(dest.spiritual_focus)
    
    return Response({
        'experience_types': sorted(list(experience_types)),
        'geography_types': sorted(list(geography_types)),
        'landscape_types': sorted(list(landscape_types)),
        'spiritual_focus': sorted(list(spiritual_focus)),
        'total_destinations': destinations.count()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def search_all_destinations(request):
    """
    Advanced search across all destinations with multiple filters (CASE-INSENSITIVE)
    """
    queryset = Destination.objects.filter(is_active=True)
    
    # Text search
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(state__icontains=q)
        )
    
    # Category filters - CASE INSENSITIVE
    experience = request.GET.get('experience')
    if experience:
        all_dests = list(queryset)
        filtered_ids = []
        for d in all_dests:
            if d.experience_types:
                if any(experience.lower() == exp.lower() for exp in d.experience_types):
                    filtered_ids.append(d.id)
        queryset = Destination.objects.filter(id__in=filtered_ids)
    
    geography = request.GET.get('geography')
    if geography:
        all_dests = list(queryset)
        filtered_ids = []
        for d in all_dests:
            if d.geography_types:
                if any(geography.lower() == geo.lower() for geo in d.geography_types):
                    filtered_ids.append(d.id)
        queryset = Destination.objects.filter(id__in=filtered_ids)
    
    landscape = request.GET.get('landscape')
    if landscape:
        all_dests = list(queryset)
        filtered_ids = []
        for d in all_dests:
            if d.landscape_types:
                if any(landscape.lower() == land.lower() for land in d.landscape_types):
                    filtered_ids.append(d.id)
        queryset = Destination.objects.filter(id__in=filtered_ids)
    
    spiritual = request.GET.get('spiritual')
    if spiritual:
        all_dests = list(queryset)
        filtered_ids = []
        for d in all_dests:
            if d.spiritual_focus:
                if any(spiritual.lower() in sf.lower() for sf in d.spiritual_focus):
                    filtered_ids.append(d.id)
        queryset = Destination.objects.filter(id__in=filtered_ids)
    
    # Location filters
    state = request.GET.get('state')
    if state:
        queryset = queryset.filter(state__iexact=state)
    
    # Budget filters
    budget_min = request.GET.get('budget_min')
    if budget_min:
        try:
            queryset = queryset.filter(budget_range_min__gte=int(budget_min))
        except ValueError:
            pass
    
    budget_max = request.GET.get('budget_max')
    if budget_max:
        try:
            queryset = queryset.filter(budget_range_max__lte=int(budget_max))
        except ValueError:
            pass
    
    # Duration filter
    max_duration = request.GET.get('max_duration')
    if max_duration:
        try:
            queryset = queryset.filter(typical_duration__lte=int(max_duration))
        except ValueError:
            pass
    
    # Difficulty filter
    difficulty = request.GET.get('difficulty')
    if difficulty:
        queryset = queryset.filter(difficulty_level__iexact=difficulty)
    
    # Climate filter
    climate = request.GET.get('climate')
    if climate:
        queryset = queryset.filter(climate_type__icontains=climate)
    
    # Sorting
    sort_by = request.GET.get('sort_by', '-popularity_score')
    queryset = queryset.order_by(sort_by)
    
    serializer = DestinationListSerializer(queryset, many=True)
    
    return Response({
        'count': queryset.count(),
        'results': serializer.data,
        'filters_applied': {
            'q': q,
            'experience': experience,
            'geography': geography,
            'landscape': landscape,
            'spiritual': spiritual,
            'state': state,
            'budget_min': budget_min,
            'budget_max': budget_max,
            'max_duration': max_duration,
            'difficulty': difficulty,
            'climate': climate
        }
    })
