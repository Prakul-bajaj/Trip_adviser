import re
import logging
from typing import Dict, List, Optional, Any
from django.db.models import Q
from destinations.models import Destination
from integrations.weather_api import WeatherAPIClient
from .context_manager import ConversationContextManager

logger = logging.getLogger(__name__)


class BudgetHandler:
    """
    Advanced budget handler with context awareness and progressive filtering
    """
    
    BUDGET_CATEGORIES = {
        'ultra_budget': {'min': 0, 'max': 15000, 'label': 'Ultra Budget', 'emoji': '💵'},
        'budget': {'min': 15000, 'max': 30000, 'label': 'Budget-Friendly', 'emoji': '💰'},
        'mid_range': {'min': 30000, 'max': 60000, 'label': 'Mid-Range', 'emoji': '💳'},
        'premium': {'min': 60000, 'max': 100000, 'label': 'Premium', 'emoji': '💎'},
        'luxury': {'min': 100000, 'max': 250000, 'label': 'Luxury', 'emoji': '👑'},
        'ultra_luxury': {'min': 250000, 'max': 1000000, 'label': 'Ultra Luxury', 'emoji': '✨'}
    }
    
    def __init__(self, session, request):
        self.session = session
        self.request = request
        self.context_mgr = ConversationContextManager(session)
        self.weather_client = WeatherAPIClient()
    
    def handle_budget_query(self, message: str, entities: Dict) -> Dict[str, Any]:
        """
        Main entry point for budget queries with full context awareness
        """
        # Extract budget from message or entities
        budget_info = self._extract_budget_info(message, entities)
        
        # Get conversation context
        context_summary = self.context_mgr.get_context_summary()
        
        # Check if we're refining existing search or doing fresh search
        is_refining = context_summary.get('is_refining', False)
        current_dest_ids = context_summary.get('current_destinations', [])
        
        if not budget_info and not is_refining:
            # No budget specified - show budget inquiry
            return self._show_budget_inquiry(context_summary)
        
        # Determine search mode
        if is_refining and current_dest_ids:
            return self._refine_by_budget(budget_info, current_dest_ids, context_summary, message)
        else:
            return self._fresh_budget_search(budget_info, context_summary, entities, message)
    
    def _extract_budget_info(self, message: str, entities: Dict) -> Optional[Dict]:
        """
        Extract budget information from message and entities
        """
        budget = entities.get('budget')
        
        if budget:
            if isinstance(budget, dict):
                return budget
            elif isinstance(budget, (int, float)):
                return {'amount': budget, 'max': budget}
        
        # Extract from message using patterns
        message_lower = message.lower()
        
        # Pattern 1: Explicit amounts "50000", "50k", "1 lakh"
        amount_patterns = [
            (r'(\d+)\s*k(?:\s|$)', lambda m: int(m.group(1)) * 1000),
            (r'(\d+)\s*lakh', lambda m: int(m.group(1)) * 100000),
            (r'(\d+)\s*lakhs', lambda m: int(m.group(1)) * 100000),
            (r'(\d{4,})', lambda m: int(m.group(1))),
        ]
        
        for pattern, converter in amount_patterns:
            match = re.search(pattern, message_lower)
            if match:
                amount = converter(match)
                
                # Check for range indicators
                if any(word in message_lower for word in ['under', 'below', 'max', 'maximum', 'up to', 'within']):
                    return {'max': amount, 'type': 'max'}
                elif any(word in message_lower for word in ['above', 'over', 'minimum', 'at least']):
                    return {'min': amount, 'type': 'min'}
                else:
                    return {'amount': amount, 'max': amount, 'type': 'exact'}
        
        # Pattern 2: Budget categories
        category_keywords = {
            'cheap': 'ultra_budget',
            'budget': 'budget',
            'affordable': 'budget',
            'moderate': 'mid_range',
            'mid-range': 'mid_range',
            'expensive': 'premium',
            'premium': 'premium',
            'luxury': 'luxury',
            'luxurious': 'luxury',
        }
        
        for keyword, category in category_keywords.items():
            if keyword in message_lower:
                budget_range = self.BUDGET_CATEGORIES[category]
                return {
                    'min': budget_range['min'],
                    'max': budget_range['max'],
                    'category': category,
                    'type': 'category'
                }
        
        return None
    
    def _show_budget_inquiry(self, context_summary: Dict) -> Dict[str, Any]:
        """
        Show budget inquiry when no budget is specified
        """
        # Check if user has shown preferences that can help
        learned_prefs = context_summary.get('learned_preferences', {})
        current_topic = context_summary.get('current_topic')
        
        message_text = "Let me help you find the perfect destinations within your budget! 💰\n\n"
        
        if current_topic:
            message_text += f"I see you're interested in **{current_topic}** destinations. "
        
        message_text += "What's your budget range?\n\n**Budget Categories:**\n\n"
        
        # Show relevant budget categories
        for category_key, budget_range in self.BUDGET_CATEGORIES.items():
            emoji = budget_range['emoji']
            label = budget_range['label']
            min_amt = budget_range['min']
            max_amt = budget_range['max']
            
            if max_amt >= 1000000:
                range_text = f"₹{min_amt:,}+"
            else:
                range_text = f"₹{min_amt:,} - ₹{max_amt:,}"
            
            message_text += f"{emoji} **{label}:** {range_text}\n"
        
        message_text += "\n💡 *Tip: You can also specify an exact amount like '50000' or '1 lakh'*"
        
        suggestions = [
            "Budget under 25000",
            "Mid-range 50000",
            "Show premium options",
            "Luxury destinations"
        ]
        
        # Add context-aware suggestion
        if current_topic:
            suggestions.insert(0, f"Budget {current_topic} under 40000")
        
        return {
            'message': message_text,
            'budget_categories': [
                {
                    'key': key,
                    'label': val['label'],
                    'range': f"₹{val['min']:,} - ₹{val['max']:,}",
                    'emoji': val['emoji']
                }
                for key, val in self.BUDGET_CATEGORIES.items()
            ],
            'suggestions': suggestions,
            'context': 'budget_inquiry',
            'needs_input': True
        }
    
    def _refine_by_budget(
        self, 
        budget_info: Dict, 
        current_dest_ids: List[str], 
        context_summary: Dict,
        message: str
    ) -> Dict[str, Any]:
        """
        Refine existing search results by budget (progressive filtering)
        """
        logger.info(f"Refining {len(current_dest_ids)} destinations by budget")
        
        # Get current destinations
        destinations = Destination.objects.filter(
            id__in=current_dest_ids,
            is_active=True
        )
        
        original_count = destinations.count()
        
        # Apply budget filter
        if budget_info.get('type') == 'max' or budget_info.get('max'):
            max_budget = budget_info.get('max') or budget_info.get('amount')
            destinations = destinations.filter(budget_range_max__lte=max_budget)
        elif budget_info.get('type') == 'min' or budget_info.get('min'):
            min_budget = budget_info['min']
            destinations = destinations.filter(budget_range_min__gte=min_budget)
        elif budget_info.get('amount'):
            amount = budget_info['amount']
            destinations = destinations.filter(
                budget_range_min__lte=amount,
                budget_range_max__gte=amount
            )
        
        filtered_count = destinations.count()
        
        # Learn budget preference
        if budget_info.get('max'):
            self.context_mgr.learn_preference('budget_max', budget_info['max'])
            self.context_mgr.learn_preference('budget_conscious', True)
        
        # Adjust ranking priorities
        self.context_mgr.adjust_ranking_priorities('budget')
        
        # Handle no results after filtering
        if filtered_count == 0:
            return self._handle_no_budget_results(
                budget_info, 
                original_count, 
                context_summary,
                message
            )
        
        # Handle too few results - suggest expansion
        if filtered_count < 2:
            expansion_suggestion = self._suggest_budget_expansion(
                budget_info,
                filtered_count,
                original_count
            )
        else:
            expansion_suggestion = ""
        
        # Sort by budget (cheapest first if budget-conscious)
        destinations = destinations.order_by('budget_range_min')[:8]
        
        # Build response
        budget_desc = self._format_budget_description(budget_info)
        
        message_text = f"I've filtered the results {budget_desc}! 🎯\n\n"
        message_text += f"Found **{filtered_count}** destinations (from {original_count}):\n\n"
        
        if expansion_suggestion:
            message_text += f"💡 {expansion_suggestion}\n\n"
        
        # Format destinations
        dest_list = []
        destination_ids = []
        
        for i, dest in enumerate(destinations, 1):
            destination_ids.append(str(dest.id))
            
            # Calculate budget match score
            budget_match_score = self._calculate_budget_match(dest, budget_info)
            
            dest_data = {
                'id': str(dest.id),
                'name': dest.name,
                'state': dest.state,
                'budget_min': dest.budget_range_min,
                'budget_max': dest.budget_range_max,
                'budget_match_score': budget_match_score,
                'experiences': dest.experience_types[:3] if dest.experience_types else []
            }
            
            dest_list.append(dest_data)
            
            # Format message
            message_text += f"{i}. **{dest.name}**, {dest.state}\n"
            message_text += f"   💰 ₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}"
            
            # Show savings if applicable
            if budget_info.get('max'):
                savings = budget_info['max'] - dest.budget_range_max
                if savings > 0:
                    message_text += f" (Save ₹{savings:,}!)"
            
            message_text += f"\n   {dest.description[:70]}...\n"
            
            # Show relevant experiences
            if dest.experience_types:
                message_text += f"   🎯 {', '.join(dest.experience_types[:3])}\n"
            
            message_text += "\n"
        
        message_text += "Which one interests you? 😊"
        
        # Update context
        constraint_applied = {
            'type': 'budget',
            'value': budget_info,
            'results_before': original_count,
            'results_after': filtered_count
        }
        
        self.context_mgr.update_active_search(message, destination_ids, constraint_applied)
        
        # Generate suggestions
        suggestions = [
            f"Tell me about {destinations.first().name}",
            f"Weather in {destinations.first().name}",
        ]
        
        if filtered_count < original_count:
            suggestions.append("Remove budget filter")
        
        suggestions.extend([
            "Add more filters",
            "Show all options"
        ])
        
        return {
            'message': message_text,
            'destinations': dest_list,
            'is_refining': True,
            'filter_applied': 'budget',
            'budget_range': budget_desc,
            'results_before': original_count,
            'results_after': filtered_count,
            'suggestions': suggestions,
            'context': 'budget_refined'
        }
    
    def _fresh_budget_search(
        self,
        budget_info: Dict,
        context_summary: Dict,
        entities: Dict,
        message: str
    ) -> Dict[str, Any]:
        """
        Perform fresh search with budget as primary filter
        """
        logger.info(f"Fresh budget search with: {budget_info}")
        
        # Start with all destinations
        destinations = Destination.objects.filter(is_active=True)
        
        # Apply budget filter
        if budget_info.get('type') == 'max' or budget_info.get('max'):
            max_budget = budget_info.get('max') or budget_info.get('amount')
            destinations = destinations.filter(budget_range_max__lte=max_budget)
        elif budget_info.get('type') == 'min' or budget_info.get('min'):
            min_budget = budget_info['min']
            destinations = destinations.filter(budget_range_min__gte=min_budget)
        elif budget_info.get('amount'):
            amount = budget_info['amount']
            destinations = destinations.filter(
                budget_range_min__lte=amount,
                budget_range_max__gte=amount
            )
        
        # Apply additional filters from context
        activities = entities.get('activities', [])
        current_topic = context_summary.get('current_topic')
        
        # Map activities to experience types
        if activities or current_topic:
            experience_types = self._map_to_experience_types(activities, current_topic)
            
            if experience_types:
                filtered_ids = []
                for dest in destinations:
                    if dest.experience_types:
                        if any(
                            any(target.lower() in exp.lower() for target in experience_types)
                            for exp in dest.experience_types
                        ):
                            filtered_ids.append(dest.id)
                
                destinations = Destination.objects.filter(
                    id__in=filtered_ids,
                    is_active=True
                )
        
        # Apply weather filtering if preferences known
        learned_prefs = context_summary.get('learned_preferences', {})
        weather_pref = learned_prefs.get('weather_preference')
        
        if weather_pref:
            destinations = self._apply_weather_filtering(destinations, weather_pref)
        
        # Sort by budget
        destinations = destinations.order_by('budget_range_min')[:10]
        
        # Handle no results
        if not destinations.exists():
            return self._handle_no_budget_results(budget_info, 0, context_summary, message)
        
        # Build response
        budget_desc = self._format_budget_description(budget_info)
        context_phrase = ""
        
        if activities:
            context_phrase = f" for {', '.join(activities)}"
        elif current_topic:
            context_phrase = f" for {current_topic}"
        
        message_text = f"Here are amazing destinations{context_phrase} {budget_desc}! 💰✨\n\n"
        
        # Format destinations with budget highlights
        dest_list = []
        destination_ids = []
        
        for i, dest in enumerate(destinations, 1):
            destination_ids.append(str(dest.id))
            
            budget_match_score = self._calculate_budget_match(dest, budget_info)
            
            dest_data = {
                'id': str(dest.id),
                'name': dest.name,
                'state': dest.state,
                'budget_min': dest.budget_range_min,
                'budget_max': dest.budget_range_max,
                'budget_match_score': budget_match_score,
                'experiences': dest.experience_types[:3] if dest.experience_types else []
            }
            
            dest_list.append(dest_data)
            
            message_text += f"{i}. **{dest.name}**, {dest.state}\n"
            message_text += f"   💰 ₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}"
            
            # Highlight great deals
            if budget_match_score > 0.8:
                message_text += " ⭐ Great Value!"
            
            message_text += f"\n   {dest.description[:70]}...\n"
            
            if dest.experience_types:
                relevant_exp = dest.experience_types[:3]
                message_text += f"   🎯 {', '.join(relevant_exp)}\n"
            
            message_text += "\n"
        
        message_text += "Which one would you like to explore? 😊"
        
        # Update context
        self.context_mgr.update_active_search(
            message,
            destination_ids,
            {'type': 'budget', 'value': budget_info}
        )
        
        # Learn preferences
        if budget_info.get('max') and budget_info['max'] < 30000:
            self.context_mgr.learn_preference('budget_conscious', True)
        
        suggestions = [
            f"Tell me about {destinations.first().name}",
            f"Plan trip to {destinations.first().name}",
            "Add duration filter",
            "Show more options"
        ]
        
        return {
            'message': message_text,
            'destinations': dest_list,
            'is_refining': False,
            'budget_range': budget_desc,
            'suggestions': suggestions,
            'context': 'fresh_budget_search'
        }
    
    def _handle_no_budget_results(
        self,
        budget_info: Dict,
        original_count: int,
        context_summary: Dict,
        message: str
    ) -> Dict[str, Any]:
        """
        Handle case when no destinations match budget criteria
        """
        budget_desc = self._format_budget_description(budget_info)
        
        message_text = f"I couldn't find destinations {budget_desc} "
        
        current_topic = context_summary.get('current_topic')
        if current_topic:
            message_text += f"for {current_topic} experiences "
        
        message_text += "😔\n\n"
        
        # Suggest alternatives
        if original_count > 0:
            message_text += "**Options:**\n"
            message_text += "• Increase your budget slightly\n"
            message_text += "• Remove some filters\n"
            message_text += "• See what's available just above your range\n\n"
            
            # Find closest destinations
            if budget_info.get('max'):
                nearby_budget = budget_info['max'] * 1.2  # 20% more
                message_text += f"💡 I found destinations around ₹{int(nearby_budget):,}. Want to see those?"
        else:
            message_text += "Let me show you popular destinations instead!"
        
        suggestions = [
            "Increase budget",
            "Remove filters",
            "Show all destinations",
            "Show popular places"
        ]
        
        if budget_info.get('max'):
            relaxed_budget = int(budget_info['max'] * 1.3)
            suggestions.insert(0, f"Show under ₹{relaxed_budget:,}")
        
        return {
            'message': message_text,
            'destinations': [],
            'budget_range': budget_desc,
            'original_count': original_count,
            'suggestions': suggestions,
            'context': 'no_budget_results',
            'alternative_action': 'increase_budget'
        }
    
    def _suggest_budget_expansion(
        self,
        budget_info: Dict,
        current_count: int,
        original_count: int
    ) -> str:
        """
        Suggest budget expansion when results are too few
        """
        if budget_info.get('max'):
            expanded_budget = int(budget_info['max'] * 1.2)
            return (
                f"Only {current_count} result(s) found. "
                f"Expanding to ₹{expanded_budget:,} would show {original_count} options."
            )
        return ""
    
    def _calculate_budget_match(self, destination: Destination, budget_info: Dict) -> float:
        """
        Calculate how well destination matches budget (0-1)
        """
        if budget_info.get('amount'):
            target = budget_info['amount']
            dest_mid = (destination.budget_range_min + destination.budget_range_max) / 2
            
            # Perfect match if destination midpoint is close to target
            diff_ratio = abs(dest_mid - target) / target
            return max(0, 1 - diff_ratio)
        
        elif budget_info.get('max'):
            max_budget = budget_info['max']
            
            # Better score for cheaper destinations
            if destination.budget_range_max <= max_budget * 0.7:
                return 1.0  # Great deal
            elif destination.budget_range_max <= max_budget * 0.85:
                return 0.8
            else:
                return 0.6
        
        return 0.5
    
    def _format_budget_description(self, budget_info: Dict) -> str:
        """
        Format budget info into readable description
        """
        if budget_info.get('category'):
            category = budget_info['category']
            return self.BUDGET_CATEGORIES[category]['label'].lower()
        
        if budget_info.get('type') == 'max' or budget_info.get('max'):
            max_amt = budget_info.get('max') or budget_info.get('amount')
            return f"under ₹{max_amt:,}"
        
        elif budget_info.get('type') == 'min' or budget_info.get('min'):
            min_amt = budget_info['min']
            return f"above ₹{min_amt:,}"
        
        elif budget_info.get('amount'):
            return f"around ₹{budget_info['amount']:,}"
        
        return "within your budget"
    
    def _map_to_experience_types(
        self,
        activities: List[str],
        current_topic: Optional[str]
    ) -> List[str]:
        """
        Map activities and topics to experience types
        """
        mapping = {
            'adventure': ['Adventure', 'Trekking', 'Mountain', 'Sports'],
            'beach': ['Beach', 'Relaxation', 'Water Sports'],
            'cultural': ['Cultural', 'Heritage', 'Historical'],
            'wildlife': ['Wildlife', 'Nature', 'Safari'],
            'spiritual': ['Spiritual', 'Religious', 'Pilgrimage'],
            'food': ['Food & Culinary', 'Culinary'],
            'relaxation': ['Relaxation', 'Wellness', 'Spa'],
            'mountain': ['Mountain', 'Hills', 'Himalayan'],
        }
        
        experience_types = []
        
        for activity in activities:
            activity_lower = activity.lower()
            if activity_lower in mapping:
                experience_types.extend(mapping[activity_lower])
        
        if current_topic and current_topic.lower() in mapping:
            experience_types.extend(mapping[current_topic.lower()])
        
        return list(set(experience_types))
    
    def _apply_weather_filtering(
        self,
        destinations,
        weather_pref: str
    ) -> 'QuerySet':
        """
        Apply weather-based filtering (basic implementation)
        """
        return destinations


# Integration function for views.py
def handle_budget_query_v2(request, session, message, entities):
    """
    Enhanced budget handler function - use this in views.py
    """
    handler = BudgetHandler(session, request)
    return handler.handle_budget_query(message, entities)