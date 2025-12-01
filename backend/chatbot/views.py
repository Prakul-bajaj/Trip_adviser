# chatbot/views.py - CLEANED VERSION
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ChatSession, Message, ConversationState
from .serializers import ChatSessionSerializer, MessageSerializer
from destinations.models import Destination
from itinerary.models import Itinerary
from recommendations.recommendation_engine import RecommendationEngine
from recommendations.models import UserBookmark, TravelAdvisory
from integrations.weather_api import WeatherAPIClient, WeatherAnalyzer
from .nlp_engine import get_nlp_engine
from .context_manager import ConversationContextManager
from datetime import datetime, timedelta
from .budget_handler import handle_budget_query_v2
import random
import re
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

# Response templates
GREETINGS = [
    "Hello! 👋 I'm your AI travel assistant. I can help you discover amazing destinations across India!",
    "Namaste! 🙏 Welcome! I'm here to help you plan your perfect journey.",
    "Hi there! ✨ Ready to explore India? I'm here to guide you!",
]

FAREWELL_RESPONSES = [
    "Goodbye! 🌍 Safe travels! Come back anytime!",
    "Happy travels! ✨ Looking forward to helping you plan your next adventure!",
    "Bon voyage! 🎒 Wishing you an amazing journey!",
]


ACTIVITY_TO_EXPERIENCE_MAP = {
    'adventure': ['Adventure', 'Trekking'],
    'beach': ['Beach'],  # ✅ ONLY Beach, nothing else!
    'cultural': ['Cultural', 'Heritage', 'Historical'],
    'wildlife': ['Wildlife', 'Nature', 'Safari'],
    'spiritual': ['Spiritual', 'Religious', 'Pilgrimage'],
    'food': ['Food & Culinary', 'Culinary'],
    'photography': ['Photography', 'Scenic'],
    'relaxation': ['Relaxation', 'Wellness', 'Spa'],
    'trekking': ['Trekking', 'Adventure'],
    'mountain': ['Mountain', 'Hills', 'Himalayan'],
    'waterfall': ['Waterfall', 'Nature'],
    'lake': ['Lake', 'Water'],
}

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    """
    Enhanced conversational endpoint with NLP
    """
    user_message = request.data.get('message', '').strip()
    session_id = request.data.get('session_id')
    
    if not user_message:
        return Response({'error': 'Message is required'}, status=400)
    
    try:
        # Get or create session
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                session = ChatSession.objects.create(
                    user=request.user,
                    title=f"Chat {datetime.now().strftime('%B %d, %Y')}"
                )
        else:
            session = ChatSession.objects.create(
                user=request.user,
                title=f"Chat {datetime.now().strftime('%B %d, %Y')}"
            )
        
        # Save user message
        user_msg = Message.objects.create(
            session=session,
            sender='user',
            content=user_message
        )
        
        # Get NLP engine
        nlp_engine = get_nlp_engine()
        
        # Get conversation context
        context_mgr = ConversationContextManager(session)
        context_summary = context_mgr.get_context_summary()
        
        # Process message with NLP (this now handles EVERYTHING)
        nlp_result = nlp_engine.process_message(
            message=user_message,
            user_id=str(request.user.id),
            session_context=context_summary
        )
        
        logger.info(f"NLP Processing Complete:")
        logger.info(f"  Intent: {nlp_result['intent']} (confidence: {nlp_result['confidence']:.2f})")
        logger.info(f"  Source: {nlp_result['source']}")
        logger.info(f"  Entities: {list(nlp_result['entities'].keys())}")
        logger.info(f"  Safe: {nlp_result['is_safe']}")
        # Handle unsafe content
        if not nlp_result['is_safe']:
            safety_response = nlp_engine.handle_inappropriate_content(
                user_message,
                nlp_result['safety_issues']
            )
            
            bot_msg = Message.objects.create(
                session=session,
                sender='bot',
                content=safety_response['message']
            )
            
            return Response({
                'message': safety_response['message'],
                'session_id': str(session.id),
                'detected_intent': 'inappropriate',
                'is_safe': False,
                'suggestions': [
                    "Show me destinations",
                    "Recommend places for me",
                    "Plan a trip"
                ]
            })
        
        # Use NLP-detected intent and entities
        detected_intent = nlp_result['intent']
        entities = nlp_result['entities']
        
        # Route to appropriate handler
        if detected_intent == 'greeting':
            bot_response = handle_greeting(request, session)
        
        elif detected_intent == 'farewell':
            bot_response = handle_farewell(request, session)
        
        elif detected_intent == 'weather':
            bot_response = handle_weather_query(request, session, user_message, entities)
        
        elif detected_intent == 'recommendation':
            bot_response = handle_personalized_recommendations(request, session, user_message, entities)
        
        elif detected_intent == 'bookmark':
            bot_response = handle_bookmark(request, session, user_message)
        
        elif detected_intent == 'safety':
            bot_response = handle_safety_check(request, session, user_message, entities)
        
        elif detected_intent == 'search':
            bot_response = handle_destination_search_v2(request, session, user_message, entities)
        
        elif detected_intent == 'trip_planning':
            bot_response = handle_itinerary_creation(request, session, user_message, entities)
        
        elif detected_intent == 'more_info':
            bot_response = handle_more_info(request, session, user_message)
        
        elif detected_intent == 'budget':
            bot_response = handle_budget_query_v2(request, session, user_message, entities)
        
        elif detected_intent == 'duration':
            if context_summary.get('current_destinations'):
                bot_response = handle_reference_query(request, session, user_message, entities)
            else:
                bot_response = handle_general_query(request, session, user_message)
        
        elif detected_intent == 'reference':
            bot_response = handle_reference_query(request, session, user_message, entities)
        
        elif detected_intent == 'attractions':
            # User asking about things to do
            bot_response = handle_destination_specific_query(
                request, session, user_message, entities, 'attractions'
            )
        
        elif detected_intent == 'restaurants':
            # User asking about places to eat
            bot_response = handle_destination_specific_query(
                request, session, user_message, entities, 'restaurants'
            )
        
        elif detected_intent == 'accommodations':
            # User asking about places to stay
            bot_response = handle_destination_specific_query(
                request, session, user_message, entities, 'accommodations'
            )
        
        else:
            bot_response = handle_general_query(request, session, user_message)
        
        # Save bot response
        bot_msg = Message.objects.create(
            session=session,
            sender='bot',
            content=bot_response['message']
        )
        
        # Update session
        session.total_messages += 2
        session.save()
        
        # Learn from interaction
        nlp_engine.learn_from_interaction(
            message=user_message,
            detected_intent=detected_intent,
            user_feedback='positive'
        )
        
        # Add metadata
        bot_response['session_id'] = str(session.id)
        bot_response['message_id'] = str(bot_msg.id)
        bot_response['detected_intent'] = detected_intent
        bot_response['nlp_confidence'] = nlp_result['confidence']
        bot_response['nlp_source'] = nlp_result['source']
        
        return Response(bot_response)
    
    except Exception as e:
        import traceback
        logger.error(f"Chat error: {traceback.format_exc()}")
        return Response({
            'message': "I'm having trouble understanding. Could you rephrase that? 🤔",
            'error': str(e),
            'suggestions': [
                "Show me destinations",
                "Recommend places for me",
                "Start fresh search"
            ]
        }, status=500)


# Handler functions (these stay mostly the same)

def handle_destination_specific_query(request, session, message, entities, query_type):
    """
    Route to specific handlers based on query type
    """
    from destinations.models import Destination
    from .context_manager import ConversationContextManager
    
    # Try to find destination from message
    destination = None
    for dest in Destination.objects.filter(is_active=True):
        if dest.name.lower() in message.lower():
            destination = dest
            break
    
    # Check context if not found
    if not destination:
        context_mgr = ConversationContextManager(session)
        context_summary = context_mgr.get_context_summary()
        dest_ids = context_summary.get('current_destinations', [])
        
        if dest_ids:
            destination = Destination.objects.filter(
                id=dest_ids[0],
                is_active=True
            ).first()
    
    if not destination:
        return {
            'message': f"Which destination are you asking about? 🤔\n\n"
                      f"Please mention the place name, for example:\n"
                      f"• 'Things to do in Goa'\n"
                      f"• 'Restaurants in Manali'\n"
                      f"• 'Where to stay in Jaipur'",
            'suggestions': [
                "Show me destinations",
                "Recommend places for me"
            ],
            'context': 'need_destination_context'
        }
    
    # Route to appropriate handler
    if query_type == 'attractions':
        return handle_attractions_query(request, session, message, destination)
    elif query_type == 'restaurants':
        return handle_restaurants_query(request, session, message, destination)
    elif query_type == 'accommodations':
        return handle_accommodations_query(request, session, message, destination)
    else:
        return handle_more_info(request, session, message)



def handle_greeting(request, session):
    """Enhanced greeting with user context"""
    greeting = random.choice(GREETINGS)
    
    bookmarks_count = UserBookmark.objects.filter(user=request.user).count()
    
    additional_msg = ""
    if bookmarks_count > 0:
        additional_msg = f"\n\nI see you have {bookmarks_count} saved destinations! Want to explore them?"
    
    return {
        'message': f"{greeting}{additional_msg}\n\nWhat can I help you with today?",
        'suggestions': [
            "Recommend destinations for me",
            "Show me my saved places" if bookmarks_count > 0 else "Show me popular destinations",
            "What's the weather like?",
            "Plan a trip"
        ],
        'context': 'greeting'
    }


def handle_farewell(request, session):
    """Handle goodbye"""
    farewell = random.choice(FAREWELL_RESPONSES)
    session.is_active = False
    session.ended_at = datetime.now()
    session.save()
    
    return {
        'message': farewell,
        'context': 'farewell',
        'session_ended': True
    }

# Add this helper function after constants
def map_activities_to_experiences(activities):
    """Convert activity list to experience types"""
    experience_types = []
    for activity in activities:
        activity_lower = activity.lower()
        if activity_lower in ACTIVITY_TO_EXPERIENCE_MAP:
            experience_types.extend(ACTIVITY_TO_EXPERIENCE_MAP[activity_lower])
    return list(set(experience_types)) 


def handle_destination_search_v2(request, session, message, entities):
    """
    FIXED: Strict filtering when user explicitly asks for a specific category
    """
    from integrations.weather_api import WeatherAPIClient
    
    # Initialize context manager
    context_mgr = ConversationContextManager(session)
    
    # Detect if user is changing topic or refining
    topic_detection = context_mgr.detect_topic_change(message, entities)
    
    # ... [topic change handling code stays same] ...
    
    # Determine if refining existing search or fresh search
    is_refining = topic_detection['action'] == 'refine'
    
    # Get current destinations if refining
    existing_dest_ids = context_mgr.get_current_destinations() if is_refining else []
    
    # Extract search parameters FROM ENTITIES
    search_query = entities.get('locations', [''])[0] if entities.get('locations') else ''
    activities = entities.get('activities', [])
    budget = entities.get('budget')
    duration = entities.get('durations', [None])[0] if entities.get('durations') else None
    weather_pref = entities.get('weather_preference')
    time_frame = entities.get('time_frame')
    
    # NEW: Get primary activity and filter mode from entities
    primary_activity = entities.get('primary_activity')  # The MAIN thing user wants
    filter_mode = entities.get('filter_mode', 'strict')  # strict or relaxed
    
    logger.info(f"Search params - Primary: {primary_activity}, Mode: {filter_mode}, Activities: {activities}")
    
    # Map activities to experience types
    experience_types = map_activities_to_experiences(activities)
    
    # NEW: If there's a primary activity, use ONLY that for strict filtering
    if primary_activity and filter_mode == 'strict':
        # Use only the primary activity's experience types
        primary_experience_types = ACTIVITY_TO_EXPERIENCE_MAP.get(primary_activity.lower(), [])
        if primary_experience_types:
            experience_types = primary_experience_types
            logger.info(f"STRICT MODE: Filtering by primary activity '{primary_activity}' -> {experience_types}")

    # PROGRESSIVE FILTERING MODE
    if is_refining and existing_dest_ids:
        logger.info(f"Refining search - filtering {len(existing_dest_ids)} existing destinations")
        
        # Start with existing destinations
        destinations = Destination.objects.filter(
            id__in=existing_dest_ids,
            is_active=True
        )
        
        # Apply new constraints
        constraint_applied = {}
        
        if budget:
            if isinstance(budget, dict):
                max_budget = budget.get('amount') or budget.get('max')
            else:
                max_budget = budget
            
            destinations = destinations.filter(budget_range_max__lte=max_budget)
            constraint_applied['type'] = 'budget'
            constraint_applied['value'] = max_budget
            context_mgr.learn_preference('budget_conscious', True)
            context_mgr.adjust_ranking_priorities('budget')
        
        if duration:
            destinations = destinations.filter(typical_duration__lte=duration)
            constraint_applied['type'] = 'duration'
            constraint_applied['value'] = duration
            context_mgr.learn_preference('short_trips', duration <= 3)
        
        # Check if results too few - expand if needed
        if destinations.count() < 2:
            logger.info(f"Only {destinations.count()} results after filtering. Expanding search...")
            
            # Relax constraints slightly
            destinations = Destination.objects.filter(is_active=True)
            
            if budget:
                destinations = destinations.filter(budget_range_max__lte=max_budget * 1.2)
            
            if duration:
                destinations = destinations.filter(typical_duration__lte=duration + 1)
            
            if experience_types:
                destinations = apply_experience_filter(
                    destinations, 
                    experience_types, 
                    strict=(filter_mode == 'strict'),
                    primary_only=(primary_activity is not None)
                )
            
            expansion_note = f"\n\n💡 I expanded the search slightly to show {destinations.count()} options."
        else:
            expansion_note = ""
        
        filtered_count = destinations.count()
        
    # FRESH SEARCH MODE
    else:
        logger.info("Fresh search initiated")
        
        destinations = Destination.objects.filter(is_active=True)
        
        # Apply location filter
        if search_query:
            destinations = destinations.filter(
                Q(name__icontains=search_query) |
                Q(state__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # NEW: Apply STRICT experience type filter
        if experience_types:
            destinations = apply_experience_filter(
                destinations, 
                experience_types, 
                strict=(filter_mode == 'strict'),
                primary_only=(primary_activity is not None)
            )
            
            logger.info(f"After experience filter: {destinations.count()} destinations")
        
        # Apply budget filter
        if budget:
            if isinstance(budget, dict):
                max_budget = budget.get('amount') or budget.get('max')
            else:
                max_budget = budget
            
            destinations = destinations.filter(budget_range_max__lte=max_budget)
        
        # Apply duration filter
        if duration:
            destinations = destinations.filter(typical_duration__lte=duration)
        
        constraint_applied = {}
        if experience_types:
            constraint_applied = {'type': 'experience', 'value': experience_types}
        
        expansion_note = ""
        filtered_count = destinations.count()
    
    # ... [rest of the function stays the same - weather filtering, response building, etc.]
    
    # WEATHER-BASED RANKING (if weather preference given)
    weather_scored_destinations = []
    weather_client = WeatherAPIClient()
    
    if weather_pref or time_frame:
        days_to_check = 5
        if time_frame:
            days_to_check = time_frame.get('end', 5)
        
        logger.info(f"Checking weather for {destinations.count()} destinations")
        
        for dest in destinations:
            try:
                current_weather = weather_client.get_current_weather(dest.latitude, dest.longitude)
                
                if not current_weather:
                    continue
                
                temp = current_weather['temperature']
                weather_score = 0.5
                weather_match = False
                weather_reason = ""
                
                if weather_pref == 'cold' and temp <= 20:
                    weather_score = 1.0 - (temp / 20)
                    weather_match = True
                    weather_reason = f"Cool {temp}°C"
                elif weather_pref == 'hot' and temp >= 28:
                    weather_score = min((temp - 28) / 12, 1.0)
                    weather_match = True
                    weather_reason = f"Warm {temp}°C"
                elif weather_pref == 'pleasant' and 18 <= temp <= 28:
                    weather_score = 1.0 - abs(temp - 23) / 10
                    weather_match = True
                    weather_reason = f"Pleasant {temp}°C"
                elif not weather_pref:
                    weather_score = 0.7 if 15 <= temp <= 30 else 0.3
                
                is_good_travel = weather_client.is_good_travel_weather(current_weather)
                if is_good_travel:
                    weather_score += 0.2
                
                weather_scored_destinations.append({
                    'destination': dest,
                    'weather_score': weather_score,
                    'current_weather': current_weather,
                    'weather_match': weather_match,
                    'weather_reason': weather_reason
                })
                
            except Exception as e:
                logger.warning(f"Weather check failed for {dest.name}: {e}")
                weather_scored_destinations.append({
                    'destination': dest,
                    'weather_score': 0.5,
                    'current_weather': None,
                    'weather_match': False,
                    'weather_reason': ""
                })
        
        weather_scored_destinations.sort(key=lambda x: x['weather_score'], reverse=True)
        destinations_list = weather_scored_destinations[:10]
    else:
        destinations = destinations.order_by('-popularity_score')[:10]
        destinations_list = [
            {
                'destination': dest,
                'weather_score': 0.5,
                'current_weather': None,
                'weather_match': False,
                'weather_reason': ""
            }
            for dest in destinations
        ]
    
    # Handle no results
    if not destinations_list:
        context_mgr.update_active_search(message, [], constraint_applied)
        
        fallback_msg = "I couldn't find destinations matching all your criteria. 😔\n\n"
        
        if is_refining:
            fallback_msg += "The filters were too restrictive. Would you like me to:\n"
            fallback_msg += "• Relax some constraints\n"
            fallback_msg += "• Start a fresh search\n"
            fallback_msg += "• Show me what you have before filtering"
        else:
            fallback_msg += "Let me show you some popular destinations instead!"
        
        return {
            'message': fallback_msg,
            'suggestions': [
                "Show popular destinations",
                "Relax budget constraints",
                "Start fresh search",
                "Show all destinations"
            ],
            'context': 'no_results_filtered'
        }
    
    # Build response message
    new_topic = topic_detection.get('new_topic') or topic_detection.get('current_topic')
    
    if is_refining:
        constraint_desc = ""
        if constraint_applied.get('type') == 'budget':
            constraint_desc = f" under ₹{constraint_applied['value']:,} budget"
        elif constraint_applied.get('type') == 'duration':
            constraint_desc = f" for {constraint_applied['value']}-day trips"
        
        message_text = f"I've filtered the previous results{constraint_desc}! 🎯\n\n"
        message_text += f"Found {len(destinations_list)} destinations that match:{expansion_note}\n\n"
    else:
        search_context = ""
        if primary_activity:
            # Emphasize the primary activity in the message
            search_context = f" {primary_activity}"
        elif experience_types:
            main_types = list(set(exp.split()[0] for exp in experience_types[:2]))
            search_context = f" {', '.join(main_types).lower()}"
        
        if weather_pref:
            search_context += f" with {weather_pref} weather"
        
        message_text = f"Here are{search_context} destinations for you! ✨\n\n"
    
    # Format destination list
    dest_list = []
    destination_ids = []
    
    for i, dest_info in enumerate(destinations_list, 1):
        dest = dest_info['destination']
        current_weather = dest_info['current_weather']
        weather_reason = dest_info['weather_reason']
        
        destination_ids.append(str(dest.id))
        
        dest_data = {
            'id': str(dest.id),
            'name': dest.name,
            'state': dest.state,
            'budget': f"₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}",
            'experiences': dest.experience_types[:3] if dest.experience_types else [],
            'duration': dest.typical_duration
        }
        
        if current_weather:
            dest_data['weather'] = {
                'temperature': current_weather['temperature'],
                'description': current_weather['description']
            }
        
        dest_list.append(dest_data)
        
        message_text += f"{i}. **{dest.name}**, {dest.state}\n"
        message_text += f"   {dest.description[:70]}...\n"
        message_text += f"   💰 ₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}\n"
        message_text += f"   📅 {dest.typical_duration} days\n"
        
        if current_weather and weather_reason:
            message_text += f"   🌤️ {weather_reason}, {current_weather['description'].title()}\n"
        
        if dest.experience_types:
            relevant = dest.experience_types[:3]
            message_text += f"   🎯 {', '.join(relevant)}\n"
        
        message_text += "\n"
    
    message_text += "Tell me which one interests you, or add more filters! 😊"
    
    # Update context
    context_mgr.update_active_search(message, destination_ids, constraint_applied)
    if new_topic:
        context_mgr.update_topic(new_topic)
    
    if activities:
        for activity in activities:
            context_mgr.learn_preference(f'likes_{activity}', True)
    
    suggestions = [
        f"Tell me about {destinations_list[0]['destination'].name}",
        f"What's the weather in {destinations_list[0]['destination'].name}?",
    ]
    
    if not is_refining or not budget:
        suggestions.append("Show budget options")
    if not is_refining or not duration:
        suggestions.append("Quick weekend trips")
    
    suggestions.append("Show more options")
    
    return {
        'message': message_text,
        'destinations': dest_list,
        'is_refining': is_refining,
        'filtered_count': filtered_count,
        'weather_filtered': bool(weather_pref or time_frame),
        'suggestions': suggestions,
        'context': 'search_results_with_context'
    }


# NEW HELPER FUNCTION: Add this right after map_activities_to_experiences
def apply_experience_filter(destinations, experience_types, strict=True, primary_only=False):
    """
    Apply experience type filtering with strict/relaxed modes
    
    Args:
        destinations: QuerySet of destinations
        experience_types: List of experience types to match
        strict: If True, destination must have EXACT match for at least one type
        primary_only: If True, destination must match the primary experience
    
    Returns:
        QuerySet of filtered destinations
    """
    filtered_ids = []
    
    logger.info(f"Applying experience filter - Strict: {strict}, Primary only: {primary_only}")
    logger.info(f"Looking for experience types: {experience_types}")
    
    for dest in destinations:
        if not dest.experience_types:
            continue
        
        dest_experiences = [exp.lower().strip() for exp in dest.experience_types]
        
        if strict or primary_only:
            # STRICT MODE: Destination MUST have one of the exact experience types
            # Example: "Beach" destination must have "Beach" in its experience_types
            matched = False
            for target_exp in experience_types:
                target_lower = target_exp.lower().strip()
                
                # Check for EXACT word match (not substring)
                for dest_exp in dest_experiences:
                    # Match if target is exact word or at start of dest_exp
                    if dest_exp == target_lower or dest_exp.startswith(target_lower + ' '):
                        matched = True
                        logger.debug(f"✓ {dest.name}: '{dest_exp}' matches '{target_lower}'")
                        break
                
                if matched:
                    break
            
            if matched:
                filtered_ids.append(dest.id)
        else:
            # RELAXED MODE: Destination can have any related experience
            # Example: "Beach" can match "Beach", "Water Sports", "Relaxation"
            for target_exp in experience_types:
                if any(target_exp.lower() in exp.lower() for exp in dest_experiences):
                    filtered_ids.append(dest.id)
                    break
    
    logger.info(f"Filtered to {len(filtered_ids)} destinations with matching experiences")
    
    return Destination.objects.filter(id__in=filtered_ids, is_active=True)


def handle_personalized_recommendations(request, session, message, entities):
    """Handle recommendations with entities from NLP engine"""
    try:
        # Get weather preferences from entities (already extracted)
        weather_pref = entities.get('weather_preference')
        time_frame = entities.get('time_frame')
        climate_pref = entities.get('climate_preference')
        activities = entities.get('activities', [])
        budget = entities.get('budget')
        
        # Initialize recommendation engine
        engine = RecommendationEngine(request.user)
        
        # Build filters
        filters = {}
        
        if budget:
            if isinstance(budget, dict):
                filters['budget_max'] = budget.get('amount') or budget.get('max')
            else:
                filters['budget_max'] = budget
        
        # Get base recommendations
        recommendations = engine.get_recommendations(filters=filters, limit=20)
        
        if not recommendations:
            return {
                'message': "Let me learn more about your preferences! 🤔\n\n"
                          "What kind of experience are you looking for?",
                'suggestions': [
                    "Adventure destinations",
                    "Beach destinations",
                    "Show me all destinations"
                ],
                'context': 'need_preferences'
            }
        
        # Weather filtering (same logic as before)
        if weather_pref or time_frame or climate_pref:
            weather_client = WeatherAPIClient()
            weather_filtered = []
            
            days_to_check = 5
            if time_frame:
                days_to_check = time_frame.get('end', 5)
            
            for rec in recommendations:
                dest = rec['destination']
                current_weather = weather_client.get_current_weather(dest.latitude, dest.longitude)
                
                if not current_weather:
                    continue
                
                temp = current_weather['temperature']
                weather_match = False
                weather_reason = ""
                
                if weather_pref == 'cold' and temp <= 20:
                    weather_match = True
                    weather_reason = f"Cool {temp}°C"
                elif weather_pref == 'hot' and temp >= 28:
                    weather_match = True
                    weather_reason = f"Warm {temp}°C"
                elif weather_pref == 'pleasant' and 18 <= temp <= 28:
                    weather_match = True
                    weather_reason = f"Pleasant {temp}°C"
                elif not weather_pref:
                    weather_match = True
                
                if climate_pref and dest.climate_type:
                    if any(climate.lower() in dest.climate_type.lower() for climate in climate_pref):
                        weather_match = True
                
                if weather_match:
                    rec['current_weather'] = current_weather
                    rec['weather_reason'] = weather_reason
                    rec['score'] *= 1.5
                    weather_filtered.append(rec)
            
            recommendations = weather_filtered
            
            if not recommendations:
                return {
                    'message': f"I couldn't find destinations with {weather_pref} weather in the next {days_to_check} days. 😔\n\n"
                              "Would you like me to show you popular destinations instead?",
                    'suggestions': [
                        "Show popular destinations",
                        "Show me all destinations",
                        "Change weather preference"
                    ],
                    'context': 'no_weather_match'
                }
            
            recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # Format response
        context_msg = ""
        if weather_pref:
            context_msg = f" with {weather_pref} weather"
        if time_frame:
            days = time_frame.get('end', 5)
            context_msg += f" for the next {days} days"
        
        message_text = f"Based on your preferences{context_msg}, here are my top recommendations! ⭐\n\n"
        
        dest_list = []
        for i, rec in enumerate(recommendations[:5], 1):
            dest = rec['destination']
            reasons = rec['reasons']
            current_weather = rec.get('current_weather')
            
            dest_info = {
                'id': str(dest.id),
                'name': dest.name,
                'state': dest.state,
                'score': rec['score'],
                'reasons': reasons
            }
            
            if current_weather:
                dest_info['weather'] = {
                    'temperature': current_weather['temperature'],
                    'description': current_weather['description'],
                    'humidity': current_weather['humidity']
                }
            
            dest_list.append(dest_info)
            
            message_text += f"{i}. **{dest.name}**, {dest.state}\n"
            message_text += f"   {dest.description[:80]}...\n"
            message_text += f"   💰 Budget: ₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}\n"
            
            if current_weather:
                temp = current_weather['temperature']
                desc = current_weather['description']
                message_text += f"   🌤️ Weather: {temp}°C, {desc.title()}\n"
                
                if rec.get('weather_reason'):
                    message_text += f"   ✨ {rec['weather_reason']}\n"
            
            if reasons:
                message_text += f"   ⭐ {reasons[0]}\n"
            message_text += "\n"
        
        message_text += "Which one interests you? I can tell you more! 😊"
        
        return {
            'message': message_text,
            'recommendations': dest_list,
            'weather_filtered': bool(weather_pref or time_frame),
            'suggestions': [
                f"Tell me about {recommendations[0]['destination'].name}",
                f"Plan a trip to {recommendations[0]['destination'].name}",
                f"Save {recommendations[0]['destination'].name}",
                "Show me more options"
            ],
            'context': 'weather_aware_recommendations'
        }
    
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        return {
            'message': "I had trouble generating recommendations. Let me show you popular destinations instead! 😊",
            'error': str(e),
            'suggestions': [
                "Show popular destinations",
                "Show me beaches",
                "Plan a trip"
            ],
            'context': 'error'
        }



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def feedback(request):
    """User provides feedback on bot response"""
    message_id = request.data.get('message_id')
    feedback_type = request.data.get('feedback')  # 'positive', 'negative', 'correction'
    correct_intent = request.data.get('correct_intent')
    
    try:
        message = Message.objects.get(id=message_id, session__user=request.user)
        
        user_message = Message.objects.filter(
            session=message.session,
            sender='user',
            timestamp__lt=message.timestamp
        ).order_by('-timestamp').first()
        
        if not user_message:
            return Response({'error': 'User message not found'}, status=404)
        
        nlp_engine = get_nlp_engine()
        
        # ✅ Re-process to get current classification
        nlp_result = nlp_engine.process_message(
            message=user_message.content,
            user_id=str(request.user.id)
        )
        
        # ✅ Learn from feedback
        nlp_engine.learn_from_interaction(
            message=user_message.content,
            detected_intent=nlp_result['intent'],
            user_feedback=feedback_type,
            correct_intent=correct_intent
        )
        
        # ✅ Log learning metrics
        logger.info(f"Learning from feedback:")
        logger.info(f"  Message: {user_message.content[:50]}...")
        logger.info(f"  Detected: {nlp_result['intent']}")
        logger.info(f"  Correct: {correct_intent or 'same'}")
        logger.info(f"  Feedback: {feedback_type}")
        
        return Response({
            'message': 'Thank you for your feedback! I\'m learning and improving. 🎓',
            'learned': True,
            'previous_intent': nlp_result['intent'],
            'corrected_to': correct_intent or nlp_result['intent']
        })
    
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return Response({'error': str(e)}, status=500)

# Class-based views remain unchanged
class ChatSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChatSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)


class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        session_id = self.kwargs['session_id']
        return Message.objects.filter(
            session_id=session_id,
            session__user=self.request.user
        ).order_by('timestamp')


# Remaining handler functions (simplified versions)

def handle_duration_filter(request, session, message, entities, days):
    """Filter existing destinations by duration"""
    from .context_manager import ConversationContextManager
    
    context_mgr = ConversationContextManager(session)
    current_dest_ids = context_mgr.get_current_destinations()
    
    if not current_dest_ids:
        return {
            'message': "Let me search for destinations first! 🔍\n\nWhat kind of places are you interested in?",
            'suggestions': ["Show beach destinations", "Show mountain destinations", "Recommend for me"],
            'context': 'no_active_search'
        }
    
    destinations = Destination.objects.filter(
        id__in=current_dest_ids,
        is_active=True,
        typical_duration__lte=days
    ).order_by('typical_duration')
    
    original_count = len(current_dest_ids)
    filtered_count = destinations.count()
    
    if filtered_count == 0:
        context_summary = context_mgr.get_context_summary()
        current_topic = context_summary.get('current_topic', '')
        
        return {
            'message': f"None of the{' ' + current_topic if current_topic else ''} destinations from the previous results fit a {days}-day trip. 😔\n\n"
                      "Would you like me to:\n"
                      f"• Show all{' ' + current_topic if current_topic else ''} destinations for {days} days\n"
                      f"• Extend to {days + 1}-{days + 2} days\n"
                      "• Remove the duration filter",
            'suggestions': [f"Show {days}-day {current_topic or 'destinations'}", f"Extend to {days + 2} days", "Remove duration filter"],
            'context': 'no_duration_match'
        }
    
    destinations = destinations[:10]
    
    message_text = f"Perfect! Here are destinations you can visit in **{days} days** 🎯\n\n"
    message_text += f"Found **{filtered_count}** suitable options (from {original_count}):\n\n"
    
    dest_list = []
    destination_ids = []
    
    for i, dest in enumerate(destinations, 1):
        destination_ids.append(str(dest.id))
        
        dest_list.append({
            'id': str(dest.id),
            'name': dest.name,
            'state': dest.state,
            'budget': f"₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}",
            'duration': dest.typical_duration,
            'experiences': dest.experience_types[:3] if dest.experience_types else []
        })
        
        message_text += f"{i}. **{dest.name}**, {dest.state}\n"
        message_text += f"   ⏱️ Perfect for {dest.typical_duration} days"
        message_text += " ✨\n" if dest.typical_duration == days else "\n"
        message_text += f"   💰 ₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}\n"
        message_text += f"   {dest.description[:70]}...\n"
        
        if dest.experience_types:
            message_text += f"   🎯 {', '.join(dest.experience_types[:3])}\n"
        message_text += "\n"
    
    message_text += "Which one would you like to explore? 😊"
    
    constraint = {'type': 'duration', 'value': days, 'results_before': original_count, 'results_after': filtered_count}
    context_mgr.update_active_search(message, destination_ids, constraint)
    context_mgr.learn_preference('prefers_short_trips', days <= 4)
    
    return {
        'message': message_text,
        'destinations': dest_list,
        'is_refining': True,
        'filter_applied': 'duration',
        'duration_days': days,
        'suggestions': [f"Tell me about {destinations.first().name}", f"Weather in {destinations.first().name}", "Show more options"],
        'context': 'duration_filtered'
    }


def handle_reference_query(request, session, message, entities):
    """Handle queries that reference previous results"""
    from .context_manager import ConversationContextManager
    
    context_mgr = ConversationContextManager(session)
    message_lower = message.lower()
    
    is_filtering_query = any(word in message_lower for word in ['which of these', 'which one', 'of these', 'from these', 'any of these', 'these', 'those'])
    
    # Check for duration filter
    duration_match = re.search(r'(?:for|in|within)?\s*(\d+)\s*days?', message_lower)
    if duration_match and is_filtering_query:
        days = int(duration_match.group(1))
        entities['duration'] = {'value': days, 'days': days}
        return handle_duration_filter(request, session, message, entities, days)
    
    # Check for budget filter
    budget_match = re.search(r'under\s+(\d+)k?|within\s+(\d+)k?|(\d+)k?\s+budget', message_lower)
    if budget_match and is_filtering_query:
        budget_str = budget_match.group(1) or budget_match.group(2) or budget_match.group(3)
        budget = int(budget_str)
        if budget < 1000:
            budget *= 1000
        entities['budget'] = {'max': budget, 'type': 'max'}
        return handle_budget_query_v2(request, session, message, entities)
    
    # Resolve single destination reference
    destination_id = context_mgr.resolve_reference(message)
    
    if not destination_id:
        current_dest_ids = context_mgr.get_current_destinations()
        
        if not current_dest_ids:
            return {
                'message': "I'm not sure which destination you're referring to. 🤔\n\nCould you tell me the name or search for destinations first?",
                'suggestions': ["Show me destinations", "Search for beaches", "Recommend places for me"],
                'context': 'no_reference_found'
            }
        
        destinations = Destination.objects.filter(id__in=current_dest_ids[:5])
        message_text = "Which destination are you asking about? 🤔\n\n"
        for i, dest in enumerate(destinations, 1):
            message_text += f"{i}. {dest.name}, {dest.state}\n"
        
        return {
            'message': message_text,
            'suggestions': [f"{dest.name}" for dest in destinations],
            'context': 'clarification_needed'
        }
    
    try:
        destination = Destination.objects.get(id=destination_id, is_active=True)
    except Destination.DoesNotExist:
        return {
            'message': "I couldn't find that destination. 😔",
            'suggestions': ["Show me destinations", "Start new search"],
            'context': 'destination_not_found'
        }
    
    context_mgr.update_mentioned_destination(str(destination.id), destination.name)
    
    # Determine what user is asking
    if any(word in message_lower for word in ['weather', 'temperature', 'climate', 'rain']):
        return handle_weather_query(request, session, f"weather in {destination.name}", {'location': destination.name})
    elif any(word in message_lower for word in ['tell me', 'more about', 'details', 'information']):
        return handle_more_info(request, session, f"tell me about {destination.name}")
    elif any(word in message_lower for word in ['plan', 'trip', 'itinerary', 'book']):
        return handle_itinerary_creation(request, session, f"plan trip to {destination.name}", {'location': destination.name})
    elif any(word in message_lower for word in ['save', 'bookmark', 'add']):
        return handle_bookmark(request, session, f"save {destination.name}")
    else:
        return handle_more_info(request, session, f"tell me about {destination.name}")


def handle_weather_query(request, session, message, entities):
    """Handle weather queries"""
    location_name = entities.get('location', '')
    
    if not location_name:
        destinations = Destination.objects.filter(is_active=True)
        for dest in destinations:
            if dest.name.lower() in message.lower():
                location_name = dest.name
                break
    
    if not location_name:
        return {
            'message': "Which destination would you like to know the weather for? 🌤️",
            'suggestions': ["Weather in Goa", "Weather in Manali", "Weather in Jaipur"],
            'context': 'need_location'
        }
    
    try:
        destination = Destination.objects.filter(name__icontains=location_name, is_active=True).first()
        
        if not destination:
            return {
                'message': f"I couldn't find '{location_name}'. Could you try another destination? 🤔",
                'suggestions': ["Weather in Goa", "Show me all destinations"],
                'context': 'location_not_found'
            }
        
        weather_client = WeatherAPIClient()
        current_weather = weather_client.get_current_weather(destination.latitude, destination.longitude)
        
        if not current_weather:
            return {
                'message': f"Sorry, I couldn't fetch weather data for {destination.name} right now. 😔",
                'suggestions': [f"Tell me more about {destination.name}", "Show me other destinations"],
                'context': 'weather_unavailable'
            }
        
        temp = current_weather['temperature']
        feels_like = current_weather['feels_like']
        description = current_weather['description']
        humidity = current_weather['humidity']
        
        is_good = weather_client.is_good_travel_weather(current_weather)
        travel_advice = "✅ Great weather for traveling!" if is_good else "⚠️ Weather conditions may not be ideal for travel." if is_good is False else ""
        
        message_text = f"**Current Weather in {destination.name}** 🌤️\n\n"
        message_text += f"🌡️ Temperature: {temp}°C (feels like {feels_like}°C)\n"
        message_text += f"☁️ Conditions: {description.title()}\n"
        message_text += f"💧 Humidity: {humidity}%\n\n"
        message_text += f"{travel_advice}\n\n"
        message_text += f"Want to know more about {destination.name}?"
        
        return {
            'message': message_text,
            'weather': current_weather,
            'destination': {'id': str(destination.id), 'name': destination.name, 'state': destination.state},
            'suggestions': [f"Tell me about {destination.name}", f"Plan a trip to {destination.name}", "Show me other destinations"],
            'context': 'weather_provided'
        }
    
    except Exception as e:
        return {
            'message': "Sorry, I encountered an error fetching weather data. 😔",
            'error': str(e),
            'suggestions': ["Try another destination", "Show me destinations"],
            'context': 'error'
        }


def handle_bookmark(request, session, message):
    """Handle bookmark/save requests"""
    destinations = Destination.objects.filter(is_active=True)
    found_dest = None
    
    for dest in destinations:
        if dest.name.lower() in message.lower():
            found_dest = dest
            break
    
    if not found_dest:
        return {
            'message': "Which destination would you like to save? 📌",
            'suggestions': ["Show me destinations", "Recommend places"],
            'context': 'need_destination'
        }
    
    bookmark, created = UserBookmark.objects.get_or_create(user=request.user, destination=found_dest)
    
    if created:
        found_dest.bookmark_count += 1
        found_dest.save()
        total_bookmarks = UserBookmark.objects.filter(user=request.user).count()
        
        return {
            'message': f"✅ {found_dest.name} has been added to your wishlist!\n\nYou now have {total_bookmarks} saved destinations. 🎉",
            'bookmark': {'id': str(bookmark.id), 'destination': found_dest.name},
            'suggestions': [f"Plan trip to {found_dest.name}", f"Weather in {found_dest.name}", "Show my bookmarks"],
            'context': 'bookmark_added'
        }
    else:
        return {
            'message': f"📌 {found_dest.name} is already in your wishlist!",
            'suggestions': [f"Remove {found_dest.name} from wishlist", f"Plan trip to {found_dest.name}", "Show my bookmarks"],
            'context': 'already_bookmarked'
        }


def handle_show_bookmarks(request, session):
    """Show user's saved destinations"""
    bookmarks = UserBookmark.objects.filter(user=request.user).select_related('destination')
    
    if not bookmarks.exists():
        return {
            'message': "You haven't saved any destinations yet! 📌\n\n"
                      "I can help you discover amazing places to add to your wishlist!",
            'suggestions': [
                "Recommend destinations for me",
                "Show popular places",
                "Show beach destinations",
                "Show mountain destinations"
            ],
            'context': 'no_bookmarks'
        }
    
    message_text = f"Here are your {bookmarks.count()} saved destinations! 💖\n\n"
    
    bookmark_list = []
    for i, bookmark in enumerate(bookmarks[:10], 1):
        dest = bookmark.destination
        bookmark_list.append({
            'id': str(dest.id),
            'name': dest.name,
            'state': dest.state,
            'saved_at': str(bookmark.created_at.date())
        })
        
        message_text += f"{i}. **{dest.name}**, {dest.state}\n"
        message_text += f"   {dest.description[:60]}...\n"
        message_text += f"   💰 ₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}\n\n"
    
    if bookmarks.count() > 10:
        message_text += f"...and {bookmarks.count() - 10} more!\n\n"
    
    message_text += "Want to explore any of these?"
    
    return {
        'message': message_text,
        'bookmarks': bookmark_list,
        'suggestions': [
            f"Tell me about {bookmarks.first().destination.name}",
            f"Plan trip to {bookmarks.first().destination.name}",
            "Remove a destination",
            "Add more destinations"
        ],
        'context': 'bookmarks_shown'
    }


def handle_safety_check(request, session, message, entities):
    """Check travel advisories and safety"""
    location_name = entities.get('location', '')
    
    if not location_name:
        destinations = Destination.objects.filter(is_active=True)
        for dest in destinations:
            if dest.name.lower() in message.lower():
                location_name = dest.name
                break
    
    if not location_name:
        return {
            'message': "Which destination are you asking about? 🛡️",
            'suggestions': ["Safety for Goa", "Safety for Manali", "Show me safe destinations"],
            'context': 'need_location'
        }
    
    destination = Destination.objects.filter(name__icontains=location_name, is_active=True).first()
    
    if not destination:
        return {
            'message': f"I couldn't find '{location_name}'. Try another destination? 🤔",
            'suggestions': ["Show all destinations"],
            'context': 'location_not_found'
        }
    
    advisories = TravelAdvisory.objects.filter(destination=destination, is_active=True).order_by('-severity')
    safety_rating = destination.safety_rating
    
    message_text = f"**Safety Information for {destination.name}** 🛡️\n\n"
    message_text += f"Overall Safety Rating: {safety_rating}/5.0 ⭐\n\n"
    
    if advisories.exists():
        message_text += f"**Current Advisories ({advisories.count()}):**\n\n"
        for adv in advisories[:3]:
            severity_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🟠', 'critical': '🔴'}.get(adv.severity, '⚪')
            message_text += f"{severity_emoji} **{adv.title}**\n"
            message_text += f"   {adv.description[:100]}...\n"
            message_text += f"   Valid until: {adv.valid_until.strftime('%B %d, %Y') if adv.valid_until else 'Ongoing'}\n\n"
    else:
        message_text += "✅ No active travel advisories!\n\n"
    
    if safety_rating >= 4.5:
        message_text += "This is generally considered a very safe destination! 👍"
    elif safety_rating >= 4.0:
        message_text += "This is a safe destination with standard precautions recommended."
    else:
        message_text += "Exercise caution and stay informed about local conditions."
    
    return {
        'message': message_text,
        'destination': {'id': str(destination.id), 'name': destination.name, 'safety_rating': safety_rating},
        'advisories_count': advisories.count(),
        'suggestions': [f"Tell me more about {destination.name}", f"Plan a trip to {destination.name}", "Show me safer alternatives"],
        'context': 'safety_info_provided'
    }


def handle_itinerary_creation(request, session, message, entities):
    """Handle trip planning"""
    destination_name = entities.get('location')
    duration = entities.get('durations', [5])[0] if entities.get('durations') else 5
    budget_info = entities.get('budget', {})
    budget = budget_info.get('amount', 40000) if isinstance(budget_info, dict) else 40000
    
    if not destination_name:
        return {
            'message': "I'd love to help you plan an amazing trip! 🎒\n\nWhere would you like to go?",
            'suggestions': ["Plan trip to Goa", "5-day trip to Manali", "Week in Kerala"],
            'context': 'need_destination'
        }
    
    destination = Destination.objects.filter(name__icontains=destination_name, is_active=True).first()
    
    if not destination:
        return {
            'message': f"Hmm, I couldn't find '{destination_name}'. 🤔\n\nWant to see available destinations?",
            'suggestions': ["Show all destinations", "Recommend destinations"],
            'context': 'destination_not_found'
        }
    
    start_date = datetime.now().date() + timedelta(days=30)
    end_date = start_date + timedelta(days=duration - 1)
    
    try:
        itinerary = Itinerary.objects.create(
            user=request.user,
            title=f"{duration}-Day Trip to {destination.name}",
            description=f"Personalized {duration}-day adventure",
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration,
            total_budget=budget,
            currency='INR'
        )
        
        message_text = f"🎉 Wonderful! Your trip to {destination.name} is ready!\n\n"
        message_text += f"📍 **Destination:** {destination.name}, {destination.state}\n"
        message_text += f"📅 **Dates:** {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}\n"
        message_text += f"⏱️ **Duration:** {duration} days\n"
        message_text += f"💰 **Budget:** ₹{budget:,}\n\n"
        message_text += "What would you like to do next?"
        
        return {
            'message': message_text,
            'itinerary': {'id': str(itinerary.id), 'title': itinerary.title, 'destination': destination.name, 'duration': duration, 'budget': budget},
            'suggestions': ["Show day-by-day plan", "Export as PDF", "Plan another trip"],
            'context': 'itinerary_created'
        }
    except Exception as e:
        return {
            'message': "Oops! I had trouble creating the itinerary. 😔\n\nLet's try again!",
            'error': str(e),
            'suggestions': [f"Tell me about {destination.name}", "Show me destinations"],
            'context': 'error'
        }


# chatbot/views.py - ADD/REPLACE this function

def handle_more_info(request, session, message):
    """
    Get comprehensive information about a destination including:
    - Basic details
    - Attractions (things to do)
    - Restaurants (where to eat)
    - Accommodations (where to stay)
    """
    from destinations.models import Destination
    from .context_manager import ConversationContextManager
    
    destinations = Destination.objects.filter(is_active=True)
    found_dest = None
    
    # Try to find destination from message
    for dest in destinations:
        if dest.name.lower() in message.lower():
            found_dest = dest
            break
    
    # If not found, check conversation context
    if not found_dest:
        context_mgr = ConversationContextManager(session)
        context_summary = context_mgr.get_context_summary()
        mentioned = context_summary.get('mentioned_destinations', [])
        
        if mentioned:
            last_dest_name = mentioned[-1]
            found_dest = Destination.objects.filter(
                name__icontains=last_dest_name,
                is_active=True
            ).first()
    
    # Still not found? Check recent bot messages
    if not found_dest:
        from .models import Message
        recent_messages = Message.objects.filter(
            session=session,
            sender='bot'
        ).order_by('-timestamp')[:5]
        
        for msg in recent_messages:
            for dest in destinations:
                if dest.name.lower() in msg.content.lower():
                    found_dest = dest
                    break
            if found_dest:
                break
    
    if not found_dest:
        return {
            'message': "Which destination would you like to know more about? 🤔\n\n"
                      "Please tell me the name of the place you're interested in!",
            'suggestions': [
                "Tell me about Goa",
                "More about Manali",
                "Show all destinations"
            ],
            'context': 'need_clarification'
        }
    
    # Build comprehensive destination information
    message_text = f"**{found_dest.name}, {found_dest.state}** ✨\n\n"
    message_text += f"{found_dest.description}\n\n"
    
    # Basic Information
    message_text += "**📍 Key Information:**\n"
    message_text += f"• **Best Time:** {', '.join(found_dest.best_time_to_visit[:3]) if found_dest.best_time_to_visit else 'Year-round'}\n"
    message_text += f"• **Typical Stay:** {found_dest.typical_duration} days\n"
    message_text += f"• **Budget:** ₹{found_dest.budget_range_min:,} - ₹{found_dest.budget_range_max:,}\n"
    message_text += f"• **Climate:** {found_dest.climate_type}\n"
    message_text += f"• **Difficulty:** {found_dest.difficulty_level.title()}\n"
    message_text += f"• **Safety Rating:** {found_dest.safety_rating}/5.0 ⭐\n\n"
    
    # Experiences
    if found_dest.experience_types:
        message_text += f"**🎯 Experiences:**\n"
        message_text += f"{', '.join(found_dest.experience_types[:6])}\n\n"
    
    # Getting There
    message_text += f"**✈️ Getting There:**\n"
    if found_dest.nearest_airport:
        message_text += f"• **Airport:** {found_dest.nearest_airport}\n"
    if found_dest.nearest_railway_station:
        message_text += f"• **Railway:** {found_dest.nearest_railway_station}\n"
    message_text += "\n"
    
    # ============================================================
    # ATTRACTIONS - Things to Do
    # ============================================================
    attractions = found_dest.destination_attractions.all()
    
    if attractions.exists():
        message_text += f"**🎪 Things to Do ({attractions.count()} attractions):**\n\n"
        
        # Group by type for better organization
        from collections import defaultdict
        attractions_by_type = defaultdict(list)
        
        for attraction in attractions[:10]:  # Show top 10
            attractions_by_type[attraction.type].append(attraction)
        
        for attr_type, attrs in attractions_by_type.items():
            message_text += f"*{attr_type}:*\n"
            for attr in attrs[:3]:  # Top 3 per type
                rating_stars = "⭐" * int(float(attr.rating)) if attr.rating else ""
                message_text += f"  • **{attr.name}** {rating_stars}\n"
                message_text += f"    {attr.description[:60]}...\n"
            message_text += "\n"
    else:
        message_text += "**🎪 Things to Do:**\n"
        message_text += "_Attraction details coming soon!_\n\n"
    
    # ============================================================
    # RESTAURANTS - Where to Eat
    # ============================================================
    restaurants = found_dest.destination_restaurants.all()
    
    if restaurants.exists():
        message_text += f"**🍽️ Where to Eat ({restaurants.count()} restaurants):**\n\n"
        
        # Group by cuisine
        cuisines = {}
        for restaurant in restaurants[:8]:  # Show top 8
            cuisine = restaurant.cuisine
            if cuisine not in cuisines:
                cuisines[cuisine] = []
            cuisines[cuisine].append(restaurant)
        
        for cuisine, rest_list in list(cuisines.items())[:4]:  # Top 4 cuisines
            message_text += f"*{cuisine} Cuisine:*\n"
            for rest in rest_list[:2]:  # Top 2 per cuisine
                rating_stars = "⭐" * int(float(rest.rating)) if rest.rating else ""
                message_text += f"  • **{rest.name}** {rating_stars}\n"
            message_text += "\n"
    else:
        message_text += "**🍽️ Where to Eat:**\n"
        message_text += "_Restaurant recommendations coming soon!_\n\n"
    
    # ============================================================
    # ACCOMMODATIONS - Where to Stay
    # ============================================================
    accommodations = found_dest.destination_accommodations.all()
    
    if accommodations.exists():
        message_text += f"**🏨 Where to Stay ({accommodations.count()} options):**\n\n"
        
        # Group by type (Luxury, Hotel, Budget, etc.)
        acc_by_type = defaultdict(list)
        
        for accommodation in accommodations[:8]:  # Show top 8
            acc_by_type[accommodation.type].append(accommodation)
        
        for acc_type, acc_list in list(acc_by_type.items())[:4]:  # Top 4 types
            message_text += f"*{acc_type}:*\n"
            for acc in acc_list[:2]:  # Top 2 per type
                rating_stars = "⭐" * int(float(acc.rating)) if acc.rating else ""
                message_text += f"  • **{acc.name}** {rating_stars}\n"
            message_text += "\n"
    else:
        message_text += "**🏨 Where to Stay:**\n"
        message_text += "_Accommodation options coming soon!_\n\n"
    
    # ============================================================
    # Additional Details
    # ============================================================
    
    # Weather Note (if applicable)
    if found_dest.avoid_months:
        message_text += f"**⚠️ Note:** Avoid visiting in {', '.join(found_dest.avoid_months[:3])} (monsoon/off-season)\n\n"
    
    # Call to Action
    message_text += "**What would you like to do next?**"
    
    # Prepare structured data for frontend
    destination_data = {
        'id': str(found_dest.id),
        'name': found_dest.name,
        'state': found_dest.state,
        'description': found_dest.description,
        'budget': {
            'min': found_dest.budget_range_min,
            'max': found_dest.budget_range_max
        },
        'duration': found_dest.typical_duration,
        'best_time': found_dest.best_time_to_visit,
        'experiences': found_dest.experience_types,
        'safety_rating': found_dest.safety_rating,
        'attractions': [
            {
                'name': attr.name,
                'type': attr.type,
                'description': attr.description,
                'rating': float(attr.rating) if attr.rating else None
            }
            for attr in attractions[:10]
        ] if attractions.exists() else [],
        'restaurants': [
            {
                'name': rest.name,
                'cuisine': rest.cuisine,
                'rating': float(rest.rating) if rest.rating else None
            }
            for rest in restaurants[:8]
        ] if restaurants.exists() else [],
        'accommodations': [
            {
                'name': acc.name,
                'type': acc.type,
                'rating': float(acc.rating) if acc.rating else None
            }
            for acc in accommodations[:8]
        ] if accommodations.exists() else []
    }
    
    # Generate context-aware suggestions
    suggestions = [
        f"Plan trip to {found_dest.name}",
        f"Weather in {found_dest.name}",
        f"Save {found_dest.name}",
    ]
    
    # Add specific suggestions based on available data
    if attractions.exists():
        top_attraction = attractions.first()
        suggestions.append(f"Tell me about {top_attraction.name}")
    
    if restaurants.exists():
        suggestions.append(f"Best restaurants in {found_dest.name}")
    
    if accommodations.exists():
        suggestions.append("Where to stay")
    
    suggestions.append("Show similar places")
    
    return {
        'message': message_text,
        'destination': destination_data,
        'has_attractions': attractions.exists(),
        'has_restaurants': restaurants.exists(),
        'has_accommodations': accommodations.exists(),
        'attractions_count': attractions.count() if attractions.exists() else 0,
        'restaurants_count': restaurants.count() if restaurants.exists() else 0,
        'accommodations_count': accommodations.count() if accommodations.exists() else 0,
        'suggestions': suggestions[:6],  # Top 6 suggestions
        'context': 'destination_details_complete'
    }

def handle_attractions_query(request, session, message, destination):
    """
    Handle queries specifically about attractions/things to do
    Example: "What can I do in Goa?", "Show me attractions in Manali"
    """
    attractions = destination.destination_attractions.all().order_by('-rating')
    
    if not attractions.exists():
        return {
            'message': f"I don't have specific attraction details for {destination.name} yet. 😔\n\n"
                      f"But {destination.name} is known for:\n"
                      f"{', '.join(destination.experience_types[:5]) if destination.experience_types else 'amazing experiences'}!\n\n"
                      f"Would you like me to:\n"
                      f"• Plan a trip to {destination.name}\n"
                      f"• Show similar destinations\n"
                      f"• Check weather conditions",
            'suggestions': [
                f"Plan trip to {destination.name}",
                f"Weather in {destination.name}",
                "Show similar places"
            ],
            'context': 'no_attractions_data'
        }
    
    message_text = f"**🎪 Things to Do in {destination.name}**\n\n"
    message_text += f"Here are the top {min(attractions.count(), 10)} attractions:\n\n"
    
    # Group by type
    from collections import defaultdict
    by_type = defaultdict(list)
    
    for attr in attractions[:15]:
        by_type[attr.type].append(attr)
    
    for attr_type, attrs in by_type.items():
        message_text += f"**{attr_type}** ({len(attrs)} places)\n"
        for i, attr in enumerate(attrs[:5], 1):
            rating_display = f"{attr.rating}⭐" if attr.rating else "New"
            message_text += f"{i}. **{attr.name}** - {rating_display}\n"
            message_text += f"   {attr.description}\n"
        message_text += "\n"
    
    message_text += f"💡 *Total {attractions.count()} attractions available in {destination.name}*"
    
    return {
        'message': message_text,
        'destination': {
            'id': str(destination.id),
            'name': destination.name,
            'state': destination.state
        },
        'attractions': [
            {
                'name': attr.name,
                'type': attr.type,
                'description': attr.description,
                'rating': float(attr.rating) if attr.rating else None
            }
            for attr in attractions[:15]
        ],
        'suggestions': [
            f"Tell me about {attractions.first().name}",
            "Where to eat here",
            "Where to stay",
            f"Plan trip to {destination.name}"
        ],
        'context': 'attractions_shown'
    }


def handle_restaurants_query(request, session, message, destination):
    """
    Handle queries about restaurants/food
    Example: "Where can I eat in Goa?", "Best restaurants in Manali"
    """
    restaurants = destination.destination_restaurants.all().order_by('-rating')
    
    if not restaurants.exists():
        return {
            'message': f"I don't have specific restaurant details for {destination.name} yet. 😔\n\n"
                      f"However, {destination.name} is known for its local cuisine!\n\n"
                      f"Would you like to:\n"
                      f"• Explore things to do in {destination.name}\n"
                      f"• Find where to stay\n"
                      f"• Plan your trip",
            'suggestions': [
                f"Things to do in {destination.name}",
                "Where to stay",
                f"Plan trip to {destination.name}"
            ],
            'context': 'no_restaurant_data'
        }
    
    message_text = f"**🍽️ Where to Eat in {destination.name}**\n\n"
    message_text += f"I found {restaurants.count()} great dining options!\n\n"
    
    # Group by cuisine
    cuisines = {}
    for rest in restaurants[:20]:
        cuisine = rest.cuisine
        if cuisine not in cuisines:
            cuisines[cuisine] = []
        cuisines[cuisine].append(rest)
    
    for cuisine, rest_list in cuisines.items():
        message_text += f"**{cuisine} Cuisine** ({len(rest_list)} restaurants)\n"
        for i, rest in enumerate(rest_list[:4], 1):
            rating_display = f"{rest.rating}⭐" if rest.rating else "New"
            message_text += f"{i}. **{rest.name}** - {rating_display}\n"
        message_text += "\n"
    
    # Add dining tips
    message_text += f"💡 *Try the local {destination.state} specialties!*"
    
    return {
        'message': message_text,
        'destination': {
            'id': str(destination.id),
            'name': destination.name,
            'state': destination.state
        },
        'restaurants': [
            {
                'name': rest.name,
                'cuisine': rest.cuisine,
                'rating': float(rest.rating) if rest.rating else None
            }
            for rest in restaurants[:20]
        ],
        'suggestions': [
            "Where to stay here",
            "Things to do here",
            f"Plan {destination.typical_duration}-day trip",
            "Show me the map"
        ],
        'context': 'restaurants_shown'
    }

def handle_accommodations_query(request, session, message, destination):
    """
    Handle queries about accommodations/hotels
    Example: "Where to stay in Goa?", "Hotels in Manali"
    """
    accommodations = destination.destination_accommodations.all().order_by('-rating')
    
    if not accommodations.exists():
        return {
            'message': f"I don't have specific accommodation details for {destination.name} yet. 😔\n\n"
                      f"But there are usually options from budget to luxury!\n"
                      f"Typical budget: ₹{destination.budget_range_min:,} - ₹{destination.budget_range_max:,}\n\n"
                      f"Would you like to:\n"
                      f"• Explore things to do in {destination.name}\n"
                      f"• Find places to eat\n"
                      f"• Plan your trip",
            'suggestions': [
                f"Things to do in {destination.name}",
                "Where to eat",
                f"Plan trip to {destination.name}"
            ],
            'context': 'no_accommodation_data'
        }
    
    message_text = f"**🏨 Where to Stay in {destination.name}**\n\n"
    message_text += f"I found {accommodations.count()} accommodation options!\n\n"
    
    # Group by type
    from collections import defaultdict
    by_type = defaultdict(list)
    
    for acc in accommodations[:20]:
        by_type[acc.type].append(acc)
    
    # Define order preference
    type_order = ['Luxury Resort', 'Boutique/Luxury', 'Hotel', 'Budget Hotel', 
                  'Homestay', 'Guest House', 'Villa', 'Cottage', 'Hostel']
    
    for acc_type in type_order:
        if acc_type in by_type:
            acc_list = by_type[acc_type]
            message_text += f"**{acc_type}** ({len(acc_list)} options)\n"
            for i, acc in enumerate(acc_list[:4], 1):
                rating_display = f"{acc.rating}⭐" if acc.rating else "New"
                message_text += f"{i}. **{acc.name}** - {rating_display}\n"
            message_text += "\n"
    
    # Add budget note
    message_text += f"💰 *Budget range: ₹{destination.budget_range_min:,} - ₹{destination.budget_range_max:,} for {destination.typical_duration} days*"
    
    return {
        'message': message_text,
        'destination': {
            'id': str(destination.id),
            'name': destination.name,
            'state': destination.state
        },
        'accommodations': [
            {
                'name': acc.name,
                'type': acc.type,
                'rating': float(acc.rating) if acc.rating else None
            }
            for acc in accommodations[:20]
        ],
        'suggestions': [
            "Where to eat here",
            "Things to do here",
            f"Plan {destination.typical_duration}-day trip",
            f"Book trip to {destination.name}"
        ],
        'context': 'accommodations_shown'
    }

def handle_general_query(request, session, message):
    """Handle general/unclear queries"""
    return {
        'message': "I'm here to help you discover amazing destinations! 🌍\n\n**I can help you with:**\n"
                  "• 🔍 Search for destinations\n• 🌤️ Check weather conditions\n"
                  "• 💰 Find places within your budget\n• 📅 Plan complete itineraries\n"
                  "• ⭐ Get personalized recommendations\n• 📌 Save favorite destinations\n\n"
                  "What would you like to explore?",
        'suggestions': ["Recommend destinations for me", "Show me popular places", "Plan a trip to Manali"],
        'context': 'general_help'
    }