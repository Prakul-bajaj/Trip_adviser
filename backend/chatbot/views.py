from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ChatSession, Message, ConversationState
from .serializers import ChatSessionSerializer, MessageSerializer
from .entity_extractor import EntityExtractor
from destinations.models import Destination
from itinerary.models import Itinerary
from recommendations.recommendation_engine import RecommendationEngine
from recommendations.models import UserBookmark, TravelAdvisory
from integrations.weather_api import WeatherAPIClient, WeatherAnalyzer
from datetime import datetime, timedelta
import random
import re
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

def get_or_create_conversation_context(session):
    """Get or create conversation context for session"""
    try:
        context, created = ConversationState.objects.get_or_create(
            session=session,
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
                    'mentioned_destinations': [],
                    'discussed_topics': [],
                    'last_search': {},
                    'preferences_learned': {},
                    'conversation_history': [],
                    'last_destinations_shown': [],  # Track shown destinations
                    'user_reactions': {}  # Track what user liked/disliked
                }
            }
        )
        return context
    except Exception as e:
        logger.error(f"Error creating conversation context: {e}")
        return None


def update_conversation_context(session, intent, entities, additional_data=None):
    """Update conversation context with memory"""
    try:
        context = get_or_create_conversation_context(session)
        if not context:
            return
        
        # Update intent
        context.last_intent = intent
        
        # Initialize context_data if None
        if not context.context_data:
            context.context_data = {
                'mentioned_destinations': [],
                'discussed_topics': [],
                'last_search': {},
                'preferences_learned': {},
                'conversation_history': [],
                'last_destinations_shown': [],
                'user_reactions': {}
            }
        
        # Update extracted info
        if entities:
            if not context.extracted_info:
                context.extracted_info = {}
            context.extracted_info.update(entities)
            
            # Track mentioned locations (handle both 'location' and 'locations')
            locations_to_track = []
            
            if 'location' in entities and entities['location']:
                locations_to_track.append(entities['location'])
            
            if 'locations' in entities and entities['locations']:
                if isinstance(entities['locations'], list):
                    locations_to_track.extend(entities['locations'])
                else:
                    locations_to_track.append(entities['locations'])
            
            # Add to mentioned destinations
            for location in locations_to_track:
                if location and location not in context.context_data.get('mentioned_destinations', []):
                    if 'mentioned_destinations' not in context.context_data:
                        context.context_data['mentioned_destinations'] = []
                    context.context_data['mentioned_destinations'].append(location)
        
        # Update additional data (merge, don't replace)
        if additional_data:
            for key, value in additional_data.items():
                if key in context.context_data and isinstance(context.context_data[key], dict) and isinstance(value, dict):
                    # Merge dictionaries
                    context.context_data[key].update(value)
                else:
                    # Replace value
                    context.context_data[key] = value
        
        # Add to conversation history (keep last 10 exchanges)
        if 'conversation_history' not in context.context_data:
            context.context_data['conversation_history'] = []
        
        conversation_entry = {
            'intent': intent,
            'timestamp': datetime.now().isoformat(),
            'entities': entities or {}
        }
        
        context.context_data['conversation_history'].append(conversation_entry)
        
        # Keep only last 10 entries
        if len(context.context_data['conversation_history']) > 10:
            context.context_data['conversation_history'] = context.context_data['conversation_history'][-10:]
        
        # Track discussed topics
        if 'discussed_topics' not in context.context_data:
            context.context_data['discussed_topics'] = []
        
        if intent not in context.context_data['discussed_topics']:
            context.context_data['discussed_topics'].append(intent)
        
        # Update interests if activities or experience types found
        if entities:
            activities = entities.get('activities', [])
            experience_types = entities.get('experience_types', [])
            
            all_interests = activities + experience_types
            
            for interest in all_interests:
                if interest and interest not in context.interests:
                    context.interests.append(interest)
        
        # Update budget if found
        if entities and 'budget' in entities:
            budget_info = entities['budget']
            if isinstance(budget_info, dict):
                context.budget = budget_info
            elif isinstance(budget_info, (int, float)):
                context.budget = {'max': budget_info}
        
        # Update dates if found
        if entities and 'dates' in entities:
            context.travel_dates = entities['dates']
        
        # Update duration if found
        if entities and 'duration' in entities:
            if not context.travel_dates:
                context.travel_dates = {}
            context.travel_dates['duration'] = entities['duration']
        
        context.save()
        
    except Exception as e:
        logger.error(f"Error updating conversation context: {e}")


def get_conversation_context_summary(session):
    """Get a summary of conversation context for reference"""
    try:
        context = get_or_create_conversation_context(session)
        if not context:
            return None
        
        context_data = context.context_data or {}
        
        summary = {
            'mentioned_destinations': context_data.get('mentioned_destinations', []),
            'last_destinations_shown': context_data.get('last_destinations_shown', []),
            'last_intent': context.last_intent,
            'interests': context.interests,
            'budget': context.budget,
            'travel_dates': context.travel_dates,
            'recent_topics': context_data.get('discussed_topics', [])[-5:],
            'last_search': context_data.get('last_search', {}),
            'preferences_learned': context_data.get('preferences_learned', {}),
            'conversation_history': context_data.get('conversation_history', [])[-5:]  # Last 5 exchanges
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting context summary: {e}")
        return None

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    """
    Main conversational endpoint with full integration
    """
    import traceback
    user_message = request.data.get('message', '').strip()
    session_id = request.data.get('session_id')
    
    if not user_message:
        return Response({
            'error': 'Message is required'
        }, status=400)
    
    try:
        # Get or create chat session
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
        
        # Save user message FIRST
        user_msg = Message.objects.create(
            session=session,
            sender='user',
            content=user_message
        )
        
        # Extract entities ONCE at the beginning
        entity_extractor = EntityExtractor()
        entities = entity_extractor.extract_entities(user_message)
        
        # Get conversation context
        context = get_or_create_conversation_context(session)
        
        # Safely combine filters
        if context and hasattr(context, 'extracted_info') and context.extracted_info:
            combined_filters = {**context.extracted_info, **entities}
        else:
            combined_filters = entities
            logger.warning("Failed to create conversation context, using defaults")
        
        # Detect intent
        message_lower = user_message.lower()
        detected_intent = None
        bot_response = None

        # 1. Greetings
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'namaste', 'start']):
            detected_intent = 'greeting'
            bot_response = handle_greeting(request, session)
        
        # 2. Farewells
        elif any(word in message_lower for word in ['bye', 'goodbye', 'exit', 'quit', 'thanks']):
            detected_intent = 'farewell'
            bot_response = handle_farewell(request, session)
        
        # 3. Weather queries
        elif any(word in message_lower for word in ['weather', 'temperature', 'rain', 'climate', 'forecast']):
            detected_intent = 'weather'
            bot_response = handle_weather_query(request, session, user_message, entities)
        
        # 4. Personalized recommendations
        elif any(word in message_lower for word in ['recommend', 'suggest', 'what should', 'which place']):
            detected_intent = 'recommendation'
            bot_response = handle_personalized_recommendations(request, session, user_message)
        
        # 5. Bookmarks/Wishlist
        elif any(word in message_lower for word in ['save', 'bookmark', 'wishlist', 'favorite', 'add to']):
            detected_intent = 'bookmarks'
            bot_response = handle_bookmark(request, session, user_message)
        
        # 6. Show saved places
        elif any(word in message_lower for word in ['my saved', 'my bookmarks', 'wishlist', 'saved places']):
            detected_intent = 'show_bookmarks'
            bot_response = handle_show_bookmarks(request, session)
        
        # 7. Safety/Advisories
        elif any(word in message_lower for word in ['safe', 'safety', 'advisory', 'warning', 'dangerous']):
            detected_intent = 'safety'
            bot_response = handle_safety_check(request, session, user_message, entities)
        
        # 8. Destination search
        elif any(word in message_lower for word in ['show', 'find', 'search', 'place', 'destination', 'where', 'best']):
            detected_intent = 'search'
            bot_response = handle_destination_search(request, session, user_message, entities)
        
        # 9. Trip planning
        elif any(word in message_lower for word in ['plan', 'trip', 'itinerary', 'create', 'schedule']):
            detected_intent = 'trip'
            bot_response = handle_itinerary_creation(request, session, user_message, entities)
        
        # 10. More info
        elif any(word in message_lower for word in ['tell me more', 'more about', 'details', 'information']):
            detected_intent = 'more_info'
            bot_response = handle_more_info(request, session, user_message)
        
        # 11. Budget queries
        elif any(word in message_lower for word in ['budget', 'cheap', 'affordable', 'expensive', 'cost']):
            detected_intent = 'budget'
            bot_response = handle_budget_query(request, session, user_message)
        
        # 12. Default/General
        else:
            detected_intent = 'general'
            bot_response = handle_general_query(request, session, user_message)
        
        # Update conversation context (only if context exists)
        if context:
            update_conversation_context(session, detected_intent, entities, {
                'last_query': user_message,
                'last_response_type': bot_response.get('context', 'unknown')
            })

        # Save bot response
        bot_msg = Message.objects.create(
            session=session,
            sender='bot',
            content=bot_response['message']
        )
        
        # Update session
        session.total_messages += 2
        session.save()
        
        # Add session info
        bot_response['session_id'] = str(session.id)
        bot_response['message_id'] = str(bot_msg.id)
        
        return Response(bot_response)
    
    except Exception as e:
        import logging
        import traceback
        error_detail = traceback.format_exc()
        logging.error(f"Chat error: {error_detail}")
        return Response({
            'message': "I'm having trouble understanding. Could you rephrase that? 🤔",
            'error': str(e),
            'traceback': error_detail,
            'suggestions': [
                "Show me destinations",
                "Recommend places for me",
                "What's the weather in Goa?",
                "Plan a trip"
            ]
        }, status=500)


def handle_greeting(request, session):
    """Enhanced greeting with user context"""
    greeting = random.choice(GREETINGS)
    
    # Check if user has bookmarks
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


def handle_weather_query(request, session, message, entities):
    """Handle weather queries using WeatherAPI"""
    location_name = entities.get('location', '')
    
    # Extract location from message
    if not location_name:
        # Try to find destination name in message
        destinations = Destination.objects.filter(is_active=True)
        for dest in destinations:
            if dest.name.lower() in message.lower():
                location_name = dest.name
                break
    
    if not location_name:
        return {
            'message': "Which destination would you like to know the weather for? 🌤️\n\n"
                      "For example:\n"
                      "• What's the weather in Goa?\n"
                      "• Tell me about Manali's climate\n"
                      "• Is it raining in Kerala?",
            'suggestions': [
                "Weather in Goa",
                "Weather in Manali",
                "Weather in Jaipur",
                "Show me destinations"
            ],
            'context': 'need_location'
        }
    
    # Find destination
    try:
        destination = Destination.objects.filter(
            name__icontains=location_name,
            is_active=True
        ).first()
        
        if not destination:
            return {
                'message': f"I couldn't find '{location_name}'. Could you try another destination? 🤔",
                'suggestions': [
                    "Weather in Goa",
                    "Show me all destinations",
                    "Recommend places"
                ],
                'context': 'location_not_found'
            }
        
        # Get weather
        weather_client = WeatherAPIClient()
        current_weather = weather_client.get_current_weather(
            destination.latitude,
            destination.longitude
        )
        
        if not current_weather:
            return {
                'message': f"Sorry, I couldn't fetch weather data for {destination.name} right now. 😔\n\n"
                          f"But I can tell you that {destination.name} has a {destination.climate_type} climate "
                          f"with temperatures typically ranging from {destination.average_temperature_range}.",
                'suggestions': [
                    f"Tell me more about {destination.name}",
                    "Show me other destinations",
                    "Plan a trip"
                ],
                'context': 'weather_unavailable'
            }
        
        # Format weather response
        temp = current_weather['temperature']
        feels_like = current_weather['feels_like']
        description = current_weather['description']
        humidity = current_weather['humidity']
        
        # Determine if good for travel
        is_good = weather_client.is_good_travel_weather(current_weather)
        
        travel_advice = ""
        if is_good:
            travel_advice = "✅ Great weather for traveling!"
        elif is_good is False:
            travel_advice = "⚠️ Weather conditions may not be ideal for travel."
        
        message_text = f"**Current Weather in {destination.name}** 🌤️\n\n"
        message_text += f"🌡️ Temperature: {temp}°C (feels like {feels_like}°C)\n"
        message_text += f"☁️ Conditions: {description.title()}\n"
        message_text += f"💧 Humidity: {humidity}%\n\n"
        message_text += f"{travel_advice}\n\n"
        message_text += f"Want to know more about {destination.name}?"
        
        return {
            'message': message_text,
            'weather': current_weather,
            'destination': {
                'id': str(destination.id),
                'name': destination.name,
                'state': destination.state
            },
            'suggestions': [
                f"Tell me about {destination.name}",
                f"Plan a trip to {destination.name}",
                "Check weather forecast",
                "Show me other destinations"
            ],
            'context': 'weather_provided'
        }
    
    except Exception as e:
        return {
            'message': "Sorry, I encountered an error fetching weather data. 😔",
            'error': str(e),
            'suggestions': [
                "Try another destination",
                "Show me destinations",
                "Plan a trip"
            ],
            'context': 'error'
        }


def handle_personalized_recommendations(request, session, message, combined_filters):
    """Handle recommendations using RecommendationEngine"""
    try:
        # Initialize recommendation engine
        engine = RecommendationEngine(request.user)
        
        # Extract any filters from message
        filters = {}
        
        # Budget extraction
        budget_match = re.search(r'(\d+)k?\s*(budget|rupees|rs)', message.lower())
        if budget_match:
            budget = int(budget_match.group(1))
            if budget < 1000:
                budget *= 1000  # Convert k to actual amount
            filters['budget_max'] = budget
        
        # Duration extraction
        duration_match = re.search(r'(\d+)\s*(day|days)', message.lower())
        if duration_match:
            # Not directly used in recommendation engine, but noted
            pass
        
        # Get recommendations
        recommendations = engine.get_recommendations(filters=filters, limit=10)
        
        if not recommendations:
            return {
                'message': "Let me learn more about your preferences! 🤔\n\n"
                          "What kind of experience are you looking for?\n"
                          "• Adventure\n"
                          "• Beach/Relaxation\n"
                          "• Cultural/Historical\n"
                          "• Spiritual\n"
                          "• Wildlife/Nature",
                'suggestions': [
                    "Adventure destinations",
                    "Beach destinations",
                    "Cultural places",
                    "Show me all destinations"
                ],
                'context': 'need_preferences'
            }
        
        # Format response
        message_text = f"Based on your preferences, here are my top recommendations for you! ⭐\n\n"
        
        dest_list = []
        for i, rec in enumerate(recommendations[:5], 1):
            dest = rec['destination']
            reasons = rec['reasons']
            
            dest_list.append({
                'id': str(dest.id),
                'name': dest.name,
                'state': dest.state,
                'score': rec['score'],
                'reasons': reasons
            })
            
            message_text += f"{i}. **{dest.name}**, {dest.state}\n"
            message_text += f"   {dest.description[:80]}...\n"
            message_text += f"   💰 Budget: ₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}\n"
            if reasons:
                message_text += f"   ✨ Why: {reasons[0]}\n"
            message_text += "\n"
        
        message_text += "Which one interests you? I can tell you more! 😊"
        
        return {
            'message': message_text,
            'recommendations': dest_list,
            'suggestions': [
                f"Tell me about {recommendations[0]['destination'].name}",
                f"Weather in {recommendations[0]['destination'].name}",
                f"Plan a trip to {recommendations[0]['destination'].name}",
                "Show me more options"
            ],
            'context': 'recommendations_provided'
        }
    
    except Exception as e:
        return {
            'message': "I had trouble generating recommendations. Let me show you popular destinations instead! 😊",
            'error': str(e),
            'suggestions': [
                "Show popular destinations",
                "Show me beaches",
                "Show me mountains",
                "Plan a trip"
            ],
            'context': 'error'
        }


def handle_bookmark(request, session, message):
    """Handle bookmark/save requests"""
    # Extract destination name
    destinations = Destination.objects.filter(is_active=True)
    found_dest = None
    
    for dest in destinations:
        if dest.name.lower() in message.lower():
            found_dest = dest
            break
    
    if not found_dest:
        return {
            'message': "Which destination would you like to save? 📌\n\n"
                      "Tell me like:\n"
                      "• Save Goa to my wishlist\n"
                      "• Add Manali to favorites\n"
                      "• Bookmark Kerala",
            'suggestions': [
                "Show me destinations",
                "Recommend places",
                "Show my bookmarks"
            ],
            'context': 'need_destination'
        }
    
    # Check if already bookmarked
    bookmark, created = UserBookmark.objects.get_or_create(
        user=request.user,
        destination=found_dest
    )
    
    if created:
        # New bookmark
        found_dest.bookmark_count += 1
        found_dest.save()
        
        total_bookmarks = UserBookmark.objects.filter(user=request.user).count()
        
        return {
            'message': f"✅ {found_dest.name} has been added to your wishlist!\n\n"
                      f"You now have {total_bookmarks} saved destinations. 🎉\n\n"
                      f"Would you like to:\n"
                      "• Plan a trip to {found_dest.name}\n"
                      "• Check the weather there\n"
                      "• See your other saved places",
            'bookmark': {
                'id': str(bookmark.id),
                'destination': found_dest.name
            },
            'suggestions': [
                f"Plan trip to {found_dest.name}",
                f"Weather in {found_dest.name}",
                "Show my bookmarks",
                "Recommend more places"
            ],
            'context': 'bookmark_added'
        }
    else:
        return {
            'message': f"📌 {found_dest.name} is already in your wishlist!\n\n"
                      f"Would you like to:\n"
                      f"• Remove it from wishlist\n"
                      f"• Plan a trip there\n"
                      f"• See other saved places",
            'suggestions': [
                f"Remove {found_dest.name} from wishlist",
                f"Plan trip to {found_dest.name}",
                "Show my bookmarks",
                "Recommend more places"
            ],
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
    
    # Extract location
    if not location_name:
        destinations = Destination.objects.filter(is_active=True)
        for dest in destinations:
            if dest.name.lower() in message.lower():
                location_name = dest.name
                break
    
    if not location_name:
        return {
            'message': "Which destination are you asking about? 🛡️\n\n"
                      "For example:\n"
                      "• Is it safe to visit Kashmir?\n"
                      "• Are there any warnings for Ladakh?\n"
                      "• Safety info for Kerala",
            'suggestions': [
                "Show me safe destinations",
                "Current travel advisories",
                "Recommend destinations"
            ],
            'context': 'need_location'
        }
    
    # Find destination
    destination = Destination.objects.filter(
        name__icontains=location_name,
        is_active=True
    ).first()
    
    if not destination:
        return {
            'message': f"I couldn't find '{location_name}'. Try another destination? 🤔",
            'suggestions': [
                "Show all destinations",
                "Safety for Goa",
                "Safety for Manali"
            ],
            'context': 'location_not_found'
        }
    
    # Check advisories
    advisories = TravelAdvisory.objects.filter(
        destination=destination,
        is_active=True
    ).order_by('-severity')
    
    safety_rating = destination.safety_rating
    
    message_text = f"**Safety Information for {destination.name}** 🛡️\n\n"
    message_text += f"Overall Safety Rating: {safety_rating}/5.0 ⭐\n\n"
    
    if advisories.exists():
        message_text += f"**Current Advisories ({advisories.count()}):**\n\n"
        for adv in advisories[:3]:
            severity_emoji = {
                'low': '🟢',
                'medium': '🟡',
                'high': '🟠',
                'critical': '🔴'
            }.get(adv.severity, '⚪')
            
            message_text += f"{severity_emoji} **{adv.title}**\n"
            message_text += f"   {adv.description[:100]}...\n"
            message_text += f"   Valid until: {adv.valid_until.strftime('%B %d, %Y') if adv.valid_until else 'Ongoing'}\n\n"
    else:
        message_text += "✅ No active travel advisories!\n\n"
    
    # General advice
    if safety_rating >= 4.5:
        message_text += "This is generally considered a very safe destination! 👍"
    elif safety_rating >= 4.0:
        message_text += "This is a safe destination with standard precautions recommended."
    else:
        message_text += "Exercise caution and stay informed about local conditions."
    
    return {
        'message': message_text,
        'destination': {
            'id': str(destination.id),
            'name': destination.name,
            'safety_rating': safety_rating
        },
        'advisories_count': advisories.count(),
        'suggestions': [
            f"Tell me more about {destination.name}",
            f"Plan a trip to {destination.name}",
            "Show me safer alternatives",
            "Current weather there"
        ],
        'context': 'safety_info_provided'
    }


def handle_destination_search(request, session, message, entities):
    """Enhanced destination search with context awareness"""
    
    # Get conversation context
    context_summary = get_conversation_context_summary(session)
    
    search_query = entities.get('locations', [''])[0] if entities.get('locations') else ''
    if not search_query:
        search_query = entities.get('location', '')
    
    activities = entities.get('activities', [])
    budget = entities.get('budget')
    
    # Map activities to experience types
    activity_to_experience_mapping = {
        'adventure': ['Adventure', 'Trekking', 'Mountain', 'Sports'],
        'beach': ['Beach', 'Relaxation', 'Water Sports'],
        'cultural': ['Cultural', 'Heritage', 'Historical'],
        'wildlife': ['Wildlife', 'Nature', 'Safari'],
        'spiritual': ['Spiritual', 'Religious', 'Pilgrimage'],
        'food': ['Food & Culinary', 'Culinary'],
        'photography': ['Photography', 'Scenic'],
        'relaxation': ['Relaxation', 'Wellness', 'Spa'],
        'trekking': ['Trekking', 'Adventure', 'Mountain'],
        'mountain': ['Mountain', 'Hills', 'Himalayan'],
        'temple': ['Spiritual', 'Pilgrimage', 'Cultural']
    }
    
    experience_types = []
    for activity in activities:
        activity_lower = activity.lower()
        if activity_lower in activity_to_experience_mapping:
            experience_types.extend(activity_to_experience_mapping[activity_lower])
    
    # Extract from message if not found in entities
    if not search_query:
        # Check if referring to previous conversation
        if context_summary and any(word in message.lower() for word in ['it', 'that place', 'there', 'similar']):
            mentioned_dests = context_summary.get('mentioned_destinations', [])
            if mentioned_dests:
                search_query = mentioned_dests[-1]
        else:
            # Try to find location keywords
            locations = ['goa', 'manali', 'kerala', 'jaipur', 'ladakh', 'rishikesh', 
                        'varanasi', 'delhi', 'mumbai', 'bangalore', 'udaipur', 'shimla']
            for loc in locations:
                if loc in message.lower():
                    search_query = loc
                    break
    
    # Check for activity keywords if no activities extracted
    if not experience_types:
        keyword_mapping = {
            'adventure': ['adventure', 'trekking', 'hiking', 'sports', 'rafting', 'climbing', 'paragliding'],
            'beach': ['beach', 'sea', 'ocean', 'coastal', 'sand', 'seaside'],
            'cultural': ['cultural', 'heritage', 'historical', 'monument', 'museum', 'ancient'],
            'wildlife': ['wildlife', 'safari', 'animals', 'nature', 'forest', 'jungle'],
            'spiritual': ['spiritual', 'temple', 'religious', 'pilgrimage', 'worship', 'shrine', 'monastery'],
            'food': ['food', 'culinary', 'cuisine', 'restaurant', 'eating'],
            'relaxation': ['relaxation', 'peaceful', 'calm', 'quiet', 'wellness', 'spa'],
            'mountain': ['mountain', 'hills', 'himalaya', 'peak', 'summit']
        }
        
        message_lower = message.lower()
        for activity_type, keywords in keyword_mapping.items():
            if any(keyword in message_lower for keyword in keywords):
                if activity_type in activity_to_experience_mapping:
                    experience_types.extend(activity_to_experience_mapping[activity_type])
                    break
    
    # Use learned preferences from context
    if not experience_types and context_summary:
        user_interests = context_summary.get('interests', [])
        if user_interests:
            for interest in user_interests[:3]:  # Use top 3 interests
                interest_lower = interest.lower()
                if interest_lower in activity_to_experience_mapping:
                    experience_types.extend(activity_to_experience_mapping[interest_lower])
    
    # Search destinations
    destinations = Destination.objects.filter(is_active=True)
    
    if search_query:
        destinations = destinations.filter(
            Q(name__icontains=search_query) |
            Q(state__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Apply experience type filter
    if experience_types:
        filtered_ids = []
        for dest in destinations:
            if dest.experience_types:
                for target_exp in experience_types:
                    if any(target_exp.lower() in exp.lower() for exp in dest.experience_types):
                        filtered_ids.append(dest.id)
                        break
        
        if filtered_ids:
            destinations = Destination.objects.filter(id__in=filtered_ids, is_active=True)
    
    # Apply budget filter
    if budget:
        if isinstance(budget, dict):
            if 'amount' in budget or 'max' in budget:
                max_budget = budget.get('amount') or budget.get('max')
                destinations = destinations.filter(budget_range_max__lte=max_budget)
        elif isinstance(budget, (int, float)):
            destinations = destinations.filter(budget_range_max__lte=budget)
    elif context_summary and context_summary.get('budget'):
        # Use budget from context
        user_budget = context_summary['budget']
        if 'max' in user_budget:
            destinations = destinations.filter(budget_range_max__lte=user_budget['max'])
    
    destinations = destinations.order_by('-popularity_score')[:8]
    
    # Handle no results
    if not destinations.exists():
        fallback_msg = "I couldn't find exact matches"
        if experience_types:
            main_types = list(set(exp.split()[0] for exp in experience_types[:2]))
            fallback_msg += f" for {', '.join(main_types).lower()} experiences"
        fallback_msg += ", but here are some popular destinations you might love! 😊"
        
        destinations = Destination.objects.filter(is_active=True).order_by('-popularity_score')[:5]
        
        dest_list = format_destination_list(destinations)
        
        # Update context with search attempt
        update_conversation_context(session, 'search', entities, {
            'last_search': {
                'query': search_query or 'general',
                'experience_types': experience_types,
                'results_count': 0,
                'timestamp': datetime.now().isoformat()
            }
        })
        
        return {
            'message': fallback_msg,
            'destinations': dest_list,
            'suggestions': [
                "Show me beach destinations",
                "Show me mountain destinations",
                "Recommend for me",
                "Tell me your preferences"
            ],
            'context': 'no_results'
        }
    
    # Format successful response
    search_context = ""
    if experience_types:
        main_types = list(set(exp.split()[0] for exp in experience_types[:2]))
        search_context = f" for {', '.join(main_types).lower()}"
    
    message_text = f"I found {destinations.count()} amazing places{search_context} for you! ✨\n\n"
    
    dest_list = []
    destination_ids = []
    
    for i, dest in enumerate(destinations, 1):
        destination_ids.append(str(dest.id))
        
        dest_list.append({
            'id': str(dest.id),
            'name': dest.name,
            'state': dest.state,
            'budget': f"₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}",
            'experiences': dest.experience_types[:3] if dest.experience_types else []
        })
        
        message_text += f"{i}. **{dest.name}**, {dest.state}\n"
        message_text += f"   {dest.description[:80]}...\n"
        message_text += f"   💰 ₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}\n"
        
        # Show relevant experience types
        if dest.experience_types:
            if experience_types:
                relevant_exps = [exp for exp in dest.experience_types 
                               if any(target.lower() in exp.lower() for target in experience_types)]
            else:
                relevant_exps = dest.experience_types[:3]
            
            if relevant_exps:
                message_text += f"   🎯 {', '.join(relevant_exps[:3])}\n"
        message_text += "\n"
    
    message_text += "Which one interests you? 😊"
    
    # Update context with successful search
    update_conversation_context(session, 'search', entities, {
        'last_search': {
            'query': search_query or 'general',
            'experience_types': experience_types,
            'activities': activities,
            'results_count': destinations.count(),
            'timestamp': datetime.now().isoformat()
        },
        'last_destinations_shown': destination_ids
    })
    
    return {
        'message': message_text,
        'destinations': dest_list,
        'search_filters': {
            'query': search_query,
            'experience_types': experience_types,
            'activities': activities,
            'budget': budget
        },
        'suggestions': [
            f"Tell me about {destinations.first().name}",
            f"Weather in {destinations.first().name}",
            f"Save {destinations.first().name}",
            "Show more options"
        ],
        'context': 'search_results'
    }


def format_destination_list(destinations):
    """Helper function to format destination list"""
    dest_list = []
    for dest in destinations:
        dest_list.append({
            'id': str(dest.id),
            'name': dest.name,
            'state': dest.state,
            'budget': f"₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}",
            'experiences': dest.experience_types[:3] if dest.experience_types else [],
            'description': dest.description[:100] + '...' if len(dest.description) > 100 else dest.description
        })
    return dest_list


def format_destination_list(destinations):
    """Helper function to format destination list"""
    return [{
        'id': str(dest.id),
        'name': dest.name,
        'state': dest.state,
        'budget': f"₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}"
    } for dest in destinations]

def handle_itinerary_creation(request, session, message, entities):
    """Handle trip planning"""
    destination_name = entities.get('location')
    duration = entities.get('duration', 5)
    budget = entities.get('budget', 40000)
    
    if not destination_name:
        return {
            'message': "I'd love to help you plan an amazing trip! 🎒\n\n"
                      "Where would you like to go?",
            'suggestions': [
                "Plan trip to Goa",
                "5-day trip to Manali",
                "Week in Kerala",
                "Show me destinations first"
            ],
            'context': 'need_destination'
        }
    
    # Find destination
    destination = Destination.objects.filter(
        name__icontains=destination_name,
        is_active=True
    ).first()
    
    if not destination:
        return {
            'message': f"Hmm, I couldn't find '{destination_name}'. 🤔\n\n"
                      f"Want to see available destinations?",
            'suggestions': [
                "Show all destinations",
                "Recommend destinations",
                "Plan trip to Goa",
                "Plan trip to Manali"
            ],
            'context': 'destination_not_found'
        }
    
    # Create itinerary
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
            'itinerary': {
                'id': str(itinerary.id),
                'title': itinerary.title,
                'destination': destination.name,
                'duration': duration,
                'budget': budget
            },
            'suggestions': [
                "Show day-by-day plan",
                "Export as PDF",
                "Modify itinerary",
                "Plan another trip"
            ],
            'context': 'itinerary_created'
        }
    except Exception as e:
        return {
            'message': "Oops! I had trouble creating the itinerary. 😔\n\nLet's try again!",
            'error': str(e),
            'suggestions': [
                f"Tell me about {destination.name}",
                "Show me destinations",
                "Recommend places"
            ],
            'context': 'error'
        }


def handle_more_info(request, session, message):
    """Get more info about a destination"""
    destinations = Destination.objects.filter(is_active=True)
    found_dest = None
    
    for dest in destinations:
        if dest.name.lower() in message.lower():
            found_dest = dest
            break
    
    if not found_dest:
        # Check recent context from session
        recent_messages = Message.objects.filter(
            session=session,
            sender='bot'
        ).order_by('-timestamp')[:3]
        
        # Try to extract destination from previous messages
        for msg in recent_messages:
            for dest in destinations:
                if dest.name.lower() in msg.content.lower():
                    found_dest = dest
                    break
            if found_dest:
                break
    
    if not found_dest:
        return {
            'message': "Which destination would you like to know more about? 🤔",
            'suggestions': [
                "Tell me about Goa",
                "More about Manali",
                "Information on Kerala",
                "Show all destinations"
            ],
            'context': 'need_clarification'
        }
    
    # Get full destination details
    message_text = f"**{found_dest.name}, {found_dest.state}** ✨\n\n"
    message_text += f"{found_dest.description}\n\n"
    
    # Key Information
    message_text += "**📍 Key Information:**\n"
    message_text += f"• Best Time: {', '.join(found_dest.best_time_to_visit[:3]) if found_dest.best_time_to_visit else 'Year-round'}\n"
    message_text += f"• Typical Stay: {found_dest.typical_duration} days\n"
    message_text += f"• Budget: ₹{found_dest.budget_range_min:,} - ₹{found_dest.budget_range_max:,}\n"
    message_text += f"• Climate: {found_dest.climate_type}\n"
    message_text += f"• Difficulty: {found_dest.difficulty_level.title()}\n\n"
    
    # Experiences
    if found_dest.experience_types:
        message_text += f"**🎯 Experiences:**\n"
        message_text += f"{', '.join(found_dest.experience_types[:5])}\n\n"
    
    # Getting there
    message_text += f"**✈️ Getting There:**\n"
    if found_dest.nearest_airport:
        message_text += f"• Airport: {found_dest.nearest_airport}\n"
    if found_dest.nearest_railway_station:
        message_text += f"• Railway: {found_dest.nearest_railway_station}\n\n"
    
    message_text += "Would you like to plan a trip here?"
    
    return {
        'message': message_text,
        'destination': {
            'id': str(found_dest.id),
            'name': found_dest.name,
            'state': found_dest.state,
            'latitude': found_dest.latitude,
            'longitude': found_dest.longitude
        },
        'suggestions': [
            f"Plan trip to {found_dest.name}",
            f"Weather in {found_dest.name}",
            f"Save {found_dest.name}",
            "Show similar places"
        ],
        'context': 'destination_details'
    }


def handle_budget_query(request, session, message, combined_filters, context):
    """Handle budget-related queries with context awareness"""
    # Extract budget from message
    budget_match = re.search(r'(\d+)k?\s*(budget|rupees|rs|inr)?', message.lower())
    
    budget = None
    if budget_match:
        budget = int(budget_match.group(1))
        if budget < 1000:
            budget *= 1000  # Convert k to actual amount
    elif combined_filters.get('budget'):
        budget_info = combined_filters['budget']
        if isinstance(budget_info, dict) and 'amount' in budget_info:
            budget = budget_info['amount']
    
    if not budget:
        # If no budget specified, show budget inquiry
        budget_categories = [
            {"name": "Budget", "range": "₹10,000 - ₹25,000", "value": 25000},
            {"name": "Mid-Range", "range": "₹25,000 - ₹50,000", "value": 50000},
            {"name": "Premium", "range": "₹50,000 - ₹1,00,000", "value": 100000},
            {"name": "Luxury", "range": "₹1,00,000+", "value": 150000},
        ]
        
        message_text = "Let me help you find destinations based on your budget! 💰\n\n"
        message_text += "**Budget Categories:**\n\n"
        
        for cat in budget_categories:
            message_text += f"• **{cat['name']}:** {cat['range']}\n"
        
        message_text += "\nWhat's your budget range?"
        
        return {
            'message': message_text,
            'budget_categories': budget_categories,
            'suggestions': [
                "Budget under 25000",
                "Mid-range 50000",
                "Luxury destinations",
                "Recommend for me"
            ],
            'context': 'budget_inquiry'
        }
    
    # ⭐ CHECK FOR PREVIOUS CONTEXT - Activities/Experience types
    activities = combined_filters.get('activities', [])
    
    # Map activities to experience types
    activity_to_experience_mapping = {
        'adventure': ['Adventure', 'Trekking', 'Mountain', 'Sports'],
        'beach': ['Beach', 'Relaxation', 'Water Sports'],
        'cultural': ['Cultural', 'Heritage', 'Historical'],
        'wildlife': ['Wildlife', 'Nature', 'Safari'],
        'spiritual': ['Spiritual', 'Religious', 'Pilgrimage'],
        'food': ['Food & Cuisine', 'Culinary'],
        'photography': ['Photography', 'Scenic', 'Natural'],
        'relaxation': ['Relaxation', 'Wellness', 'Spa'],
    }
    
    experience_types = []
    for activity in activities:
        if activity in activity_to_experience_mapping:
            experience_types.extend(activity_to_experience_mapping[activity])
    
    # Build query
    destinations = Destination.objects.filter(
        is_active=True,
        budget_range_min__lte=budget
    )
    
    # ⭐ APPLY EXPERIENCE FILTER IF IN CONTEXT
    if experience_types:
        filtered_ids = []
        for dest in destinations:
            if dest.experience_types:
                for target_exp in experience_types:
                    if any(target_exp.lower() in exp.lower() for exp in dest.experience_types):
                        filtered_ids.append(dest.id)
                        break
        destinations = Destination.objects.filter(id__in=filtered_ids, is_active=True)
    
    destinations = destinations.order_by('budget_range_min')[:8]
    
    if not destinations.exists():
        return {
            'message': f"I couldn't find destinations for ₹{budget:,} budget" + 
                      (f" with {', '.join(activities)} experiences" if activities else "") + ". 😔\n\n"
                      f"Try increasing your budget or let me recommend based on your preferences!",
            'suggestions': [
                "Recommend destinations for me",
                "Show budget destinations",
                "Show all destinations"
            ],
            'context': 'no_budget_results'
        }
    
    # ⭐ CONTEXT-AWARE MESSAGE
    context_phrase = ""
    if activities:
        context_phrase = f" for {', '.join(activities)} experiences"
    
    message_text = f"Here are amazing destinations{context_phrase} within ₹{budget:,} budget! 💰\n\n"
    
    dest_list = []
    for i, dest in enumerate(destinations, 1):
        dest_list.append({
            'id': str(dest.id),
            'name': dest.name,
            'state': dest.state,
            'budget': f"₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}",
            'experiences': dest.experience_types[:3] if dest.experience_types else []
        })
        
        message_text += f"{i}. **{dest.name}**, {dest.state}\n"
        message_text += f"   💰 ₹{dest.budget_range_min:,} - ₹{dest.budget_range_max:,}\n"
        message_text += f"   {dest.description[:70]}...\n"
        
        # Show relevant experiences
        if dest.experience_types:
            relevant = [exp for exp in dest.experience_types if any(t.lower() in exp.lower() for t in experience_types)] if experience_types else dest.experience_types[:3]
            if relevant:
                message_text += f"   🎯 {', '.join(relevant[:3])}\n"
        message_text += "\n"
    
    message_text += "Which one interests you? 😊"
    
    return {
        'message': message_text,
        'destinations': dest_list,
        'budget_filter': budget,
        'experience_filter': activities,
        'suggestions': [
            f"Tell me about {destinations.first().name}",
            f"Plan trip to {destinations.first().name}",
            "Show more options",
            "Increase budget"
        ],
        'context': 'budget_results_with_filters'
    }


def handle_general_query(request, session, message):
    """Handle general/unclear queries"""
    return {
        'message': "I'm here to help you discover amazing destinations! 🌍\n\n"
                  "**I can help you with:**\n"
                  "• 🔍 Search for destinations\n"
                  "• 🌤️ Check weather conditions\n"
                  "• 💰 Find places within your budget\n"
                  "• 📅 Plan complete itineraries\n"
                  "• ⭐ Get personalized recommendations\n"
                  "• 📌 Save favorite destinations\n"
                  "• 🛡️ Check safety advisories\n\n"
                  "What would you like to explore?",
        'suggestions': [
            "Recommend destinations for me",
            "Show me popular places",
            "What's the weather in Goa?",
            "Plan a trip to Manali",
            "Show budget destinations"
        ],
        'context': 'general_help'
    }


# Keep existing class-based views
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