from rest_framework import generics, status, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404
from destinations.models import Destination, Attraction, Restaurant, Accommodation
from .models import UserRecommendation, UserBookmark, TravelAdvisory
from .serializers import (
    DestinationSerializer, 
    DestinationListSerializer,
    AttractionSerializer,
    RestaurantSerializer,
    AccommodationSerializer,
    UserRecommendationSerializer,
    UserBookmarkSerializer,
    TravelAdvisorySerializer
)
from .recommendation_engine import RecommendationEngine
from users.models import UserInteraction


class RecommendationListView(generics.ListAPIView):
    """
    Get personalized recommendations for the authenticated user
    """
    serializer_class = UserRecommendationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserRecommendation.objects.filter(
            user=self.request.user
        ).select_related('destination').order_by('-recommendation_score', '-created_at')[:20]
    
    def list(self, request, *args, **kwargs):
        # Generate fresh recommendations
        engine = RecommendationEngine(request.user)
        
        # Get filter parameters
        filters = {}
        if request.query_params.get('budget_min'):
            filters['budget_min'] = int(request.query_params.get('budget_min'))
        if request.query_params.get('budget_max'):
            filters['budget_max'] = int(request.query_params.get('budget_max'))
        if request.query_params.get('travel_month'):
            filters['travel_month'] = request.query_params.get('travel_month')
        
        # Get recommendations
        recommendations = engine.get_recommendations(filters=filters, limit=20)
        
        # Format response
        response_data = []
        for rec in recommendations:
            dest_data = DestinationListSerializer(rec['destination']).data
            response_data.append({
                'destination': dest_data,
                'score': rec['score'],
                'reasons': rec['reasons']
            })
        
        return Response({
            'count': len(response_data),
            'results': response_data
        })


class DestinationListView(generics.ListAPIView):
    """
    List all active destinations with optional filtering
    """
    serializer_class = DestinationListSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Destination.objects.filter(is_active=True)
        
        # Apply filters from query params
        state = self.request.query_params.get('state')
        if state:
            queryset = queryset.filter(state__icontains=state)
        
        geography = self.request.query_params.getlist('geography_types')
        if geography:
            queryset = queryset.filter(geography_types__overlap=geography)
        
        experience = self.request.query_params.getlist('experience_types')
        if experience:
            queryset = queryset.filter(experience_types__overlap=experience)
        
        budget_min = self.request.query_params.get('budget_min')
        budget_max = self.request.query_params.get('budget_max')
        if budget_min and budget_max:
            queryset = queryset.filter(
                budget_range_min__gte=int(budget_min),
                budget_range_max__lte=int(budget_max)
            )
        
        # Sorting
        sort_by = self.request.query_params.get('sort_by', '-popularity_score')
        valid_sorts = {
            'popularity': '-popularity_score',
            'name': 'name',
            'budget': 'budget_range_min',
            'rating': '-safety_rating'
        }
        queryset = queryset.order_by(valid_sorts.get(sort_by, '-popularity_score'))
        
        return queryset


class DestinationDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a destination
    """
    serializer_class = DestinationSerializer
    permission_classes = [AllowAny]
    queryset = Destination.objects.filter(is_active=True)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Track view interaction
        if request.user.is_authenticated:
            UserInteraction.objects.create(
                user=request.user,
                interaction_type='view',
                destination_id=instance.id,
                destination_name=instance.name
            )
            
            # Increment view count
            instance.view_count += 1
            instance.save(update_fields=['view_count'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class DestinationSearchView(views.APIView):
    """
    Advanced search with multiple filters
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = DestinationSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        filters = serializer.validated_data
        queryset = Destination.objects.filter(is_active=True)
        
        # Text search
        query = filters.get('query')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(state__icontains=query)
            )
        
        # State filter
        state = filters.get('state')
        if state:
            queryset = queryset.filter(state__iexact=state)
        
        # Array filters
        if filters.get('geography_types'):
            queryset = queryset.filter(geography_types__overlap=filters['geography_types'])
        
        if filters.get('experience_types'):
            queryset = queryset.filter(experience_types__overlap=filters['experience_types'])
        
        if filters.get('landscape_types'):
            queryset = queryset.filter(landscape_types__overlap=filters['landscape_types'])
        
        # Budget filter
        budget_min = filters.get('budget_min')
        budget_max = filters.get('budget_max')
        if budget_min is not None and budget_max is not None:
            queryset = queryset.filter(
                budget_range_min__gte=budget_min,
                budget_range_max__lte=budget_max
            )
        
        # Difficulty level
        difficulty = filters.get('difficulty_level')
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)
        
        # Minimum rating
        min_rating = filters.get('min_rating')
        if min_rating:
            queryset = queryset.filter(safety_rating__gte=min_rating)
        
        # Travel month
        travel_month = filters.get('travel_month')
        if travel_month:
            queryset = queryset.filter(best_time_to_visit__contains=[travel_month])
        
        # Sorting
        sort_by = filters.get('sort_by', 'popularity')
        sort_mapping = {
            'popularity': '-popularity_score',
            'name': 'name',
            'budget': 'budget_range_min',
            'rating': '-safety_rating'
        }
        queryset = queryset.order_by(sort_mapping.get(sort_by, '-popularity_score'))
        
        # Save search history
        if request.user.is_authenticated:
            from users.models import UserSearchHistory
            UserSearchHistory.objects.create(
                user=request.user,
                query=query or '',
                filters_applied=filters,
                results_count=queryset.count()
            )
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = DestinationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DestinationListSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            from rest_framework.pagination import PageNumberPagination
            self._paginator = PageNumberPagination()
            self._paginator.page_size = 20
        return self._paginator
    
    def paginate_queryset(self, queryset):
        return self.paginator.paginate_queryset(queryset, self.request, view=self)
    
    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)


class PopularDestinationsView(generics.ListAPIView):
    """
    Get popular destinations
    """
    serializer_class = DestinationListSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
    def get_queryset(self):
        return Destination.objects.filter(
            is_active=True
        ).order_by('-popularity_score', '-view_count')[:10]


class UserBookmarkListView(generics.ListCreateAPIView):
    """
    List user bookmarks or create new bookmark
    """
    serializer_class = UserBookmarkSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserBookmark.objects.filter(
            user=self.request.user
        ).select_related('destination').order_by('-created_at')
    
    def perform_create(self, serializer):
        destination = get_object_or_404(
            Destination,
            id=self.request.data.get('destination_id')
        )
        
        # Track bookmark interaction
        UserInteraction.objects.create(
            user=self.request.user,
            interaction_type='bookmark',
            destination_id=destination.id,
            destination_name=destination.name
        )
        
        # Increment bookmark count
        destination.bookmark_count += 1
        destination.save(update_fields=['bookmark_count'])
        
        serializer.save(user=self.request.user)


class UserBookmarkToggleView(views.APIView):
    """
    Toggle bookmark for a destination
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, destination_id):
        destination = get_object_or_404(Destination, id=destination_id, is_active=True)
        
        bookmark, created = UserBookmark.objects.get_or_create(
            user=request.user,
            destination=destination
        )
        
        if not created:
            # Bookmark exists, remove it
            bookmark.delete()
            destination.bookmark_count = max(0, destination.bookmark_count - 1)
            destination.save(update_fields=['bookmark_count'])
            
            return Response({
                'bookmarked': False,
                'message': 'Bookmark removed'
            })
        else:
            # New bookmark created
            UserInteraction.objects.create(
                user=request.user,
                interaction_type='bookmark',
                destination_id=destination.id,
                destination_name=destination.name
            )
            
            destination.bookmark_count += 1
            destination.save(update_fields=['bookmark_count'])
            
            return Response({
                'bookmarked': True,
                'message': 'Bookmark added',
                'bookmark': UserBookmarkSerializer(bookmark).data
            }, status=status.HTTP_201_CREATED)
    
    def delete(self, request, destination_id):
        destination = get_object_or_404(Destination, id=destination_id)
        bookmark = get_object_or_404(
            UserBookmark,
            user=request.user,
            destination=destination
        )
        
        bookmark.delete()
        destination.bookmark_count = max(0, destination.bookmark_count - 1)
        destination.save(update_fields=['bookmark_count'])
        
        return Response({
            'message': 'Bookmark removed'
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def destination_stats(request):
    """
    Get overall destination statistics
    """
    stats = {
        'total_destinations': Destination.objects.filter(is_active=True).count(),
        'total_attractions': Attraction.objects.filter(is_active=True).count(),
        'total_restaurants': Restaurant.objects.filter(is_active=True).count(),
        'total_accommodations': Accommodation.objects.filter(is_active=True).count(),
        'states_covered': Destination.objects.filter(is_active=True).values('state').distinct().count(),
        'active_advisories': TravelAdvisory.objects.filter(is_active=True).count(),
    }
    
    return Response(stats)