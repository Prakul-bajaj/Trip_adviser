# chatbot/context_manager.py - UPDATED VERSION

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from .models import ConversationState, ChatSession
from destinations.models import Destination

logger = logging.getLogger(__name__)


class ConversationContextManager:
    """
    Enhanced context manager with LOCATION MEMORY
    Tracks which locations user has mentioned/discussed for smart reference resolution
    """
    
    def __init__(self, session: ChatSession):
        self.session = session
        self.context = self._load_or_create_context()
    
    def _load_or_create_context(self) -> ConversationState:
        """Load existing context or create new one"""
        context, created = ConversationState.objects.get_or_create(
            session=self.session,
            defaults={
                'current_flow': 'general',
                'current_step': 'initial',
                'travel_dates': {},
                'budget': {},
                'companions': {},
                'interests': [],
                'constraints': [],
                'extracted_info': {},
                'context_data': {
                    'conversation_flow': {
                        'current_topic': None,
                        'topic_history': [],
                        'topic_switches': 0,
                        'last_topic_change': None
                    },
                    'active_search': {
                        'initial_query': None,
                        'constraints_applied': [],
                        'results_evolution': [],
                        'current_destinations': [],
                        'current_destination_ids': [],
                        'is_refining': False,
                        'search_mode': 'fresh'
                    },
                    'mentioned_entities': {
                        'destinations': [],
                        'last_discussed_destination': None,
                        'references': {}
                    },
                    # NEW: Location memory for smart reference resolution
                    'location_memory': {
                        'last_discussed_location': None,  # {id, name, timestamp}
                        'location_history': [],  # List of all mentioned locations
                        'location_context': {}  # Additional context per location
                    },
                    'user_preferences_learned': {},
                    'rankings_applied': {
                        'weather_priority': 0.35,
                        'resource_priority': 0.20,
                        'safety_priority': 0.15,
                        'popularity_priority': 0.15,
                        'budget_priority': 0.10,
                        'user_preference_priority': 0.05
                    },
                    'last_query': None,
                    'last_response_type': None
                }
            }
        )
        return context
    
    def update_location_context(self, destination_id: str, destination_name: str, 
                                 interaction_type: str = 'discussed'):
        """
        NEW: Track location mentions for smart reference resolution
        
        Args:
            destination_id: The destination ID
            destination_name: The destination name
            interaction_type: 'discussed', 'searched', 'asked_about', 'selected'
        """
        context_data = self.context.context_data or {}
        
        if 'location_memory' not in context_data:
            context_data['location_memory'] = {
                'last_discussed_location': None,
                'location_history': [],
                'location_context': {}
            }
        
        location_memory = context_data['location_memory']
        
        # Update last discussed location
        location_memory['last_discussed_location'] = {
            'id': destination_id,
            'name': destination_name,
            'timestamp': datetime.now().isoformat(),
            'interaction_type': interaction_type
        }
        
        # Add to history if not already present
        location_entry = {
            'id': destination_id,
            'name': destination_name,
            'timestamp': datetime.now().isoformat(),
            'interaction_type': interaction_type
        }
        
        # Check if already in history
        existing = next(
            (loc for loc in location_memory['location_history'] if loc['id'] == destination_id),
            None
        )
        
        if not existing:
            location_memory['location_history'].append(location_entry)
        else:
            # Update timestamp and interaction type
            existing['timestamp'] = datetime.now().isoformat()
            existing['interaction_type'] = interaction_type
        
        # Keep only last 10 locations
        location_memory['location_history'] = location_memory['location_history'][-10:]
        
        # Also update old mentioned_entities for backward compatibility
        if 'mentioned_entities' not in context_data:
            context_data['mentioned_entities'] = {}
        
        context_data['mentioned_entities']['last_discussed_destination'] = destination_id
        context_data['mentioned_entities']['last_discussed_name'] = destination_name
        
        self.context.context_data = context_data
        self.context.save()
        
        logger.info(f"✓ Location context updated: {destination_name} ({interaction_type})")
    
    def get_last_discussed_location(self) -> Optional[Dict]:
        """
        Get the last location user discussed
        Returns: {id, name, timestamp, interaction_type} or None
        """
        context_data = self.context.context_data or {}
        location_memory = context_data.get('location_memory', {})
        return location_memory.get('last_discussed_location')
    
    def get_location_history(self, limit: int = 5) -> List[Dict]:
        """
        Get recent location history
        Returns: List of {id, name, timestamp, interaction_type}
        """
        context_data = self.context.context_data or {}
        location_memory = context_data.get('location_memory', {})
        history = location_memory.get('location_history', [])
        return history[-limit:] if history else []
    
    def was_location_discussed(self, location_name: str) -> bool:
        """Check if a location was recently discussed"""
        history = self.get_location_history(limit=10)
        return any(
            loc['name'].lower() == location_name.lower() 
            for loc in history
        )
    
    def get_context_for_nlp(self) -> Dict[str, Any]:
        """
        Get context dictionary for NLP engine
        Includes location memory for smart reference resolution
        """
        context_data = self.context.context_data or {}
        
        return {
            'current_topic': context_data.get('conversation_flow', {}).get('current_topic'),
            'last_intent': self.context.last_intent,
            'current_destinations': self.get_current_destinations(),
            'mentioned_destinations': context_data.get('mentioned_entities', {}).get('destinations', []),
            'last_discussed_location': self.get_last_discussed_location(),  # NEW
            'location_history': self.get_location_history(),  # NEW
            'is_refining': context_data.get('active_search', {}).get('is_refining', False),
            'constraints_applied': context_data.get('active_search', {}).get('constraints_applied', []),
        }
    
    def detect_topic_change(self, user_message: str, new_entities: Dict) -> Dict[str, Any]:
        """Detect if user is changing topic or refining current search"""
        context_data = self.context.context_data or {}
        current_topic = context_data.get('conversation_flow', {}).get('current_topic')
        
        new_topic = self._extract_topic_from_message(user_message, new_entities)
        
        if not current_topic:
            return {
                'action': 'fresh',
                'confidence': 1.0,
                'new_topic': new_topic
            }
        
        # Check explicit change indicators
        change_indicators = [
            'actually', 'instead', 'rather', 'change my mind', 
            'forget that', 'never mind', 'let\'s try', 'how about',
            'show me something else', 'different', 'other'
        ]
        
        message_lower = user_message.lower()
        explicit_change = any(indicator in message_lower for indicator in change_indicators)
        
        topic_similarity = self._calculate_topic_similarity(current_topic, new_topic)
        
        if explicit_change and topic_similarity < 0.3:
            return {
                'action': 'clear',
                'confidence': 0.95,
                'new_topic': new_topic,
                'reason': 'explicit_change'
            }
        
        if self._is_refinement_query(user_message, new_entities):
            return {
                'action': 'refine',
                'confidence': 0.9,
                'new_topic': current_topic,
                'constraint_added': self._extract_constraint_type(user_message, new_entities)
            }
        
        if topic_similarity < 0.4 and new_topic:
            return {
                'action': 'confirm',
                'confidence': 0.7,
                'current_topic': current_topic,
                'new_topic': new_topic,
                'message': f"You were asking about {current_topic}. Do you want to switch to {new_topic}?"
            }
        
        return {
            'action': 'continue',
            'confidence': 0.8,
            'new_topic': current_topic
        }
    
    def _extract_topic_from_message(self, message: str, entities: Dict) -> Optional[str]:
        """Extract main topic from message"""
        message_lower = message.lower()
        
        topic_keywords = {
            'beach': ['beach', 'coastal', 'sea', 'ocean', 'seaside'],
            'mountain': ['mountain', 'hill', 'peak', 'himalaya', 'altitude'],
            'adventure': ['adventure', 'trekking', 'rafting', 'paragliding', 'sports'],
            'spiritual': ['temple', 'spiritual', 'religious', 'pilgrimage', 'monastery'],
            'cultural': ['cultural', 'heritage', 'historical', 'monument', 'museum'],
            'wildlife': ['wildlife', 'safari', 'jungle', 'animals', 'nature'],
            'relaxation': ['relax', 'peaceful', 'quiet', 'spa', 'wellness'],
            'food': ['food', 'culinary', 'cuisine', 'restaurant']
        }
        
        if entities.get('activities'):
            return entities['activities'][0]
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return topic
        
        if entities.get('locations'):
            return f"destination:{entities['locations'][0]}"
        
        return None
    
    def _calculate_topic_similarity(self, topic1: Optional[str], topic2: Optional[str]) -> float:
        """Calculate similarity between two topics (0-1)"""
        if not topic1 or not topic2:
            return 0.0
        
        if topic1 == topic2:
            return 1.0
        
        related_groups = [
            {'beach', 'coastal', 'island'},
            {'mountain', 'hill', 'trek', 'adventure'},
            {'spiritual', 'temple', 'religious'},
            {'cultural', 'historical', 'heritage'},
            {'wildlife', 'nature', 'safari'}
        ]
        
        topic1_lower = topic1.lower()
        topic2_lower = topic2.lower()
        
        for group in related_groups:
            if topic1_lower in group and topic2_lower in group:
                return 0.6
        
        return 0.0
    
    def _is_refinement_query(self, message: str, entities: Dict) -> bool:
        """Check if message is refining existing search"""
        refinement_indicators = [
            'my budget', 'under', 'within', 'only', 'just',
            'need', 'must', 'should', 'prefer', 'want',
            'days', 'week', 'weekend', 'cheap', 'affordable'
        ]
        
        message_lower = message.lower()
        has_constraint = any(indicator in message_lower for indicator in refinement_indicators)
        has_constraint_entities = bool(
            entities.get('budget') or 
            entities.get('duration') or 
            entities.get('person_count')
        )
        
        reference_words = ['these', 'those', 'them', 'which one', 'the first', 'any of']
        has_reference = any(ref in message_lower for ref in reference_words)
        
        return (has_constraint or has_constraint_entities or has_reference)
    
    def _extract_constraint_type(self, message: str, entities: Dict) -> str:
        """Extract what type of constraint is being added"""
        if entities.get('budget'):
            return 'budget'
        elif entities.get('duration'):
            return 'duration'
        elif entities.get('person_count'):
            return 'group_size'
        elif 'safe' in message.lower():
            return 'safety'
        elif 'weather' in message.lower() or 'temperature' in message.lower():
            return 'weather'
        else:
            return 'general'
    
    def update_active_search(self, query: str, results: List[str], constraint: Optional[Dict] = None):
        """Update active search context"""
        context_data = self.context.context_data or {}
        
        if 'active_search' not in context_data:
            context_data['active_search'] = {}
        
        active_search = context_data['active_search']
        
        if not active_search.get('initial_query'):
            active_search['initial_query'] = query
            active_search['is_refining'] = False
            active_search['search_mode'] = 'fresh'
            active_search['results_evolution'] = []
        
        step = len(active_search.get('results_evolution', [])) + 1
        active_search['results_evolution'].append({
            'step': step,
            'count': len(results),
            'query': query,
            'timestamp': datetime.now().isoformat()
        })
        
        active_search['current_destination_ids'] = results
        active_search['is_refining'] = constraint is not None
        
        if constraint:
            if 'constraints_applied' not in active_search:
                active_search['constraints_applied'] = []
            
            active_search['constraints_applied'].append({
                **constraint,
                'timestamp': datetime.now().isoformat()
            })
        
        self.context.context_data = context_data
        self.context.save()
    
    def get_current_destinations(self) -> List[str]:
        """Get list of destination IDs from current search"""
        context_data = self.context.context_data or {}
        active_search = context_data.get('active_search', {})
        return active_search.get('current_destination_ids', [])
    
    def resolve_reference(self, message: str) -> Optional[str]:
        """
        Resolve pronouns and references (it, there, the first one, etc.)
        Returns: destination_id or None
        """
        message_lower = message.lower()
        current_dest_ids = self.get_current_destinations()
        
        if not current_dest_ids:
            return None
        
        if any(word in message_lower for word in ['first', '1st', 'top']):
            return current_dest_ids[0] if current_dest_ids else None
        
        if any(word in message_lower for word in ['second', '2nd']):
            return current_dest_ids[1] if len(current_dest_ids) > 1 else None
        
        if 'last' in message_lower:
            return current_dest_ids[-1] if current_dest_ids else None
        
        if any(word in message_lower for word in ['it', 'that', 'there']):
            context_data = self.context.context_data or {}
            mentioned = context_data.get('mentioned_entities', {})
            return mentioned.get('last_discussed_destination')
        
        return None
    
    def update_mentioned_destination(self, destination_id: str, destination_name: str):
        """
        Track which destination was just discussed
        This is now just a wrapper for update_location_context
        """
        self.update_location_context(destination_id, destination_name, 'discussed')
    
    def clear_context(self, keep_preferences: bool = True):
        """Clear context for topic change"""
        context_data = self.context.context_data or {}
        
        current_topic = context_data.get('conversation_flow', {}).get('current_topic')
        if current_topic:
            if 'conversation_flow' not in context_data:
                context_data['conversation_flow'] = {}
            
            flow = context_data['conversation_flow']
            if 'topic_history' not in flow:
                flow['topic_history'] = []
            
            flow['topic_history'].append(current_topic)
            flow['topic_switches'] = flow.get('topic_switches', 0) + 1
            flow['last_topic_change'] = datetime.now().isoformat()
        
        context_data['active_search'] = {
            'initial_query': None,
            'constraints_applied': [],
            'results_evolution': [],
            'current_destinations': [],
            'current_destination_ids': [],
            'is_refining': False,
            'search_mode': 'fresh'
        }
        
        context_data['mentioned_entities'] = {
            'destinations': [],
            'last_discussed_destination': None,
            'references': {}
        }
        
        # DON'T clear location memory - keep it for ongoing conversation
        # Only clear if explicitly requested
        
        if not keep_preferences:
            context_data['user_preferences_learned'] = {}
        
        self.context.context_data = context_data
        self.context.save()
    
    def update_topic(self, new_topic: str):
        """Update current topic"""
        context_data = self.context.context_data or {}
        
        if 'conversation_flow' not in context_data:
            context_data['conversation_flow'] = {}
        
        context_data['conversation_flow']['current_topic'] = new_topic
        
        self.context.context_data = context_data
        self.context.save()
    
    def learn_preference(self, preference_key: str, preference_value: Any):
        """Learn user preference from conversation"""
        context_data = self.context.context_data or {}
        
        if 'user_preferences_learned' not in context_data:
            context_data['user_preferences_learned'] = {}
        
        context_data['user_preferences_learned'][preference_key] = preference_value
        
        self.context.context_data = context_data
        self.context.save()
    
    def adjust_ranking_priorities(self, constraint_type: str):
        """Adjust ranking weights based on what user is asking about"""
        context_data = self.context.context_data or {}
        
        if 'rankings_applied' not in context_data:
            context_data['rankings_applied'] = {
                'weather_priority': 0.35,
                'resource_priority': 0.20,
                'safety_priority': 0.15,
                'popularity_priority': 0.15,
                'budget_priority': 0.10,
                'user_preference_priority': 0.05
            }
        
        rankings = context_data['rankings_applied']
        
        if constraint_type == 'budget':
            rankings['budget_priority'] = 0.30
            rankings['weather_priority'] = 0.25
        elif constraint_type == 'safety':
            rankings['safety_priority'] = 0.35
        elif constraint_type == 'weather':
            rankings['weather_priority'] = 0.45
        
        self.context.context_data = context_data
        self.context.save()
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation context"""
        context_data = self.context.context_data or {}
        
        return {
            'current_topic': context_data.get('conversation_flow', {}).get('current_topic'),
            'is_refining': context_data.get('active_search', {}).get('is_refining', False),
            'current_destinations': self.get_current_destinations(),
            'constraints_applied': context_data.get('active_search', {}).get('constraints_applied', []),
            'learned_preferences': context_data.get('user_preferences_learned', {}),
            'ranking_priorities': context_data.get('rankings_applied', {}),
            'last_discussed_location': self.get_last_discussed_location(),  # NEW
            'location_history': self.get_location_history()  # NEW
        }