import numpy as np
from django.db.models import Q, Count, Avg
from sklearn.metrics.pairwise import cosine_similarity
from destinations.models import Destination, Attraction, Restaurant, Accommodation
from .models import UserRecommendation, UserBookmark
from users.models import UserInteraction, TravelPreferences
from utils.constants import RECOMMENDATION_WEIGHTS
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Core recommendation engine using hybrid approach:
    - Content-based filtering (user preferences + destination features)
    - Collaborative filtering (user similarity)
    - Popularity-based ranking
    - Context-aware filtering (weather, season, budget)
    """
    
    def __init__(self, user):
        self.user = user
        self.preferences = user.travel_preferences
        self.weights = RECOMMENDATION_WEIGHTS
    
    def get_recommendations(self, filters=None, limit=20):
        """
        Get personalized recommendations for user
        """
        # Check cache first
        cache_key = f"recommendations_{self.user.id}_{str(filters)}"
        cached_results = cache.get(cache_key)
        if cached_results:
            return cached_results
        
        # Get all active destinations
        destinations = Destination.objects.filter(is_active=True)
        
        # Apply filters
        if filters:
            destinations = self._apply_filters(destinations, filters)
        
        # Calculate scores for each destination
        scored_destinations = []
        for destination in destinations:
            score = self._calculate_recommendation_score(destination, filters)
            if score > 0:
                scored_destinations.append({
                    'destination': destination,
                    'score': score,
                    'reasons': self._get_recommendation_reasons(destination)
                })
        
        # Sort by score
        scored_destinations.sort(key=lambda x: x['score'], reverse=True)
        
        # Get top recommendations
        recommendations = scored_destinations[:limit]
        
        # Cache results for 1 hour
        cache.set(cache_key, recommendations, 3600)
        
        # Save recommendations to database
        self._save_recommendations(recommendations)
        
        return recommendations
    
    def _calculate_recommendation_score(self, destination, filters):
        """
        Calculate overall recommendation score using weighted sum
        """
        # Preference match score
        preference_score = self._calculate_preference_score(destination)
        
        # Collaborative filtering score
        collaborative_score = self._calculate_collaborative_score(destination)
        
        # Content similarity score
        content_score = self._calculate_content_similarity(destination)
        
        # Popularity score (normalized)
        popularity_score = min(destination.popularity_score / 100, 1.0)
        
        # Context score (weather, season, etc.)
        context_score = self._calculate_context_score(destination, filters)
        
        # Weighted sum
        total_score = (
            self.weights['user_preference'] * preference_score +
            self.weights['collaborative_filtering'] * collaborative_score +
            self.weights['content_similarity'] * content_score +
            self.weights['popularity'] * popularity_score
        ) * context_score
        
        return total_score
    
    def _calculate_preference_score(self, destination):
        """
        Score based on user's explicit preferences
        """
        score = 0.0
        matches = 0
        total_checks = 0
        
        # Geography match
        if self.preferences.preferred_geographies:
            total_checks += 1
            for geo in destination.geography_types:
                if geo in self.preferences.preferred_geographies:
                    matches += 1
                    break
        
        # Experience match
        if self.preferences.preferred_experiences:
            total_checks += 1
            for exp in destination.experience_types:
                if exp in self.preferences.preferred_experiences:
                    matches += 1
                    break
        
        # Landscape match
        if self.preferences.preferred_landscapes:
            total_checks += 1
            for landscape in destination.landscape_types:
                if landscape in self.preferences.preferred_landscapes:
                    matches += 1
                    break
        
        # Climate match
        if self.preferences.preferred_climates:
            total_checks += 1
            if destination.climate_type in self.preferences.preferred_climates:
                matches += 1
        
        # Budget match
        if self.preferences.typical_budget_range:
            total_checks += 1
            from utils.constants import BUDGET_RANGES
            budget_range = BUDGET_RANGES.get(self.preferences.typical_budget_range, (0, float('inf')))
            if budget_range[0] <= destination.budget_range_min <= budget_range[1]:
                matches += 1
        
        if total_checks > 0:
            score = matches / total_checks
        
        return score
    
    def _calculate_collaborative_score(self, destination):
        """
        Score based on similar users' preferences
        """
        # Find users with similar preferences
        similar_users = self._find_similar_users()
        
        if not similar_users:
            return 0.0
        
        # Check how many similar users liked this destination
        interactions = UserInteraction.objects.filter(
            user__in=similar_users,
            destination_id=destination.id,
            interaction_type__in=['click', 'bookmark', 'view']
        ).count()
        
        # Normalize by number of similar users
        score = min(interactions / len(similar_users), 1.0)
        
        return score
    
    def _find_similar_users(self, limit=50):
        """
        Find users with similar travel preferences
        """
        # Simple implementation - can be enhanced with embeddings
        similar_preferences = TravelPreferences.objects.exclude(
            user=self.user
        ).filter(
            preferred_geographies__overlap=self.preferences.preferred_geographies
        ) | TravelPreferences.objects.exclude(
            user=self.user
        ).filter(
            preferred_experiences__overlap=self.preferences.preferred_experiences
        )
        
        user_ids = similar_preferences.values_list('user_id', flat=True)[:limit]
        return list(user_ids)
    
    def _calculate_content_similarity(self, destination):
        """
        Calculate similarity using embeddings (if available)
        """
        # Placeholder - implement with actual embeddings
        # This would use sentence transformers or similar
        return 0.5  # Default medium similarity
    
    def _calculate_context_score(self, destination, filters):
        """
        Score based on context (season, weather, current events)
        """
        score = 1.0
        
        if filters:
            # Season/month check
            if 'travel_month' in filters:
                month = filters['travel_month']
                if month in destination.avoid_months:
                    score *= 0.3  # Heavily penalize
                elif month in destination.best_time_to_visit:
                    score *= 1.2  # Boost
            
            # Weather check (would integrate with weather API)
            # Placeholder for now
            
            # Active advisories check
            from .models import TravelAdvisory
            critical_advisories = TravelAdvisory.objects.filter(
                destination=destination,
                is_active=True,
                severity='critical'
            ).exists()
            
            if critical_advisories:
                score *= 0.1  # Heavy penalty for critical advisories
        
        return min(score, 1.5)  # Cap the boost
    
    def _get_recommendation_reasons(self, destination):
        """
        Generate human-readable reasons for recommendation
        """
        reasons = []
        
        # Check preference matches
        if any(geo in self.preferences.preferred_geographies for geo in destination.geography_types):
            reasons.append("Matches your geography preferences")
        
        if any(exp in self.preferences.preferred_experiences for exp in destination.experience_types):
            reasons.append("Matches your experience interests")
        
        if destination.popularity_score > 75:
            reasons.append("Popular destination")
        
        if destination.rating > 4.0:
            reasons.append("Highly rated by travelers")
        
        return reasons[:3]  # Return top 3 reasons
    
    def _apply_filters(self, queryset, filters):
        """
        Apply various filters to queryset
        """
        if 'budget_min' in filters and 'budget_max' in filters:
            queryset = queryset.filter(
                budget_range_min__gte=filters['budget_min'],
                budget_range_max__lte=filters['budget_max']
            )
        
        if 'geography_types' in filters:
            queryset = queryset.filter(geography_types__overlap=filters['geography_types'])
        
        if 'experience_types' in filters:
            queryset = queryset.filter(experience_types__overlap=filters['experience_types'])
        
        if 'state' in filters:
            queryset = queryset.filter(state__iexact=filters['state'])
        
        if 'accessibility_required' in filters:
            queryset = queryset.filter(
                accessibility_features__overlap=filters['accessibility_required']
            )
        
        if 'duration_days' in filters:
            # Filter by destinations suitable for the trip duration
            duration = filters['duration_days']
            queryset = queryset.filter(
                typical_duration__lte=duration + 2,  # Allow some flexibility
                typical_duration__gte=max(1, duration - 2)
            )
        
        return queryset
    
    def _save_recommendations(self, recommendations):
        """
        Save recommendations to database for tracking
        """
        for rec in recommendations:
            UserRecommendation.objects.create(
                user=self.user,
                destination=rec['destination'],
                recommendation_score=rec['score'],
                recommendation_reason={'reasons': rec['reasons']},
                algorithm_used='hybrid'
            )