from .models import ConversationState
from recommendations.recommendation_engine import RecommendationEngine
from destinations.models import Destination
import random


class ConversationManager:
    """
    Manage conversation flow and generate appropriate responses
    """
    
    def __init__(self, session, user):
        self.session = session
        self.user = user
        self.state = self._get_or_create_state()
    
    def _get_or_create_state(self):
        """Get or create conversation state"""
        state, _ = ConversationState.objects.get_or_create(session=self.session)
        return state
    
    def generate_response(self, message_text, detected_intent, confidence):
        """
        Generate appropriate response based on intent and context
        """
        response_handlers = {
            'greeting': self.handle_greeting,
            'destination_query': self.handle_destination_query,
            'budget_query': self.handle_budget_query,
            'weather_query': self.handle_weather_query,
            'itinerary_request': self.handle_itinerary_request,
            'travel_dates': self.handle_travel_dates,
            'companion_info': self.handle_companion_info,
            'goodbye': self.handle_goodbye,
        }
        
        handler = response_handlers.get(detected_intent, self.handle_general)
        response = handler(message_text)
        
        # Add intent to response
        response['intent'] = detected_intent
        response['confidence'] = confidence
        
        return response
    
    def handle_greeting(self, message_text):
        """Handle greeting messages"""
        greetings = [
            "Hello! I'm your travel assistant. I can help you plan your perfect trip. Where would you like to go?",
            "Hi there! Ready to explore? Tell me about your dream destination!",
            "Hey! I'm excited to help you plan an amazing trip. What kind of experience are you looking for?"
        ]
        
        # Check if user has preferences set
        if not self.user.travel_preferences.onboarding_completed:
            return {
                'content': random.choice(greetings) + " First, let me learn about your preferences. Do you prefer mountains, beaches, or cultural cities?",
                'quick_replies': [
                    {'text': 'Mountains', 'value': 'mountains'},
                    {'text': 'Beaches', 'value': 'beaches'},
                    {'text': 'Cultural Cities', 'value': 'cultural'},
                ]
            }
        
        return {
            'content': random.choice(greetings),
            'quick_replies': []
        }
    
    def handle_destination_query(self, message_text):
        """Handle destination queries"""
        # Check if we have enough info for recommendations
        missing_info = self._check_missing_info()
        
        if missing_info:
            return self._ask_for_missing_info(missing_info[0])
        
        # Generate recommendations
        engine = RecommendationEngine(self.user)
        filters = self._build_filters_from_context()
        recommendations = engine.get_recommendations(filters=filters, limit=5)
        
        if not recommendations:
            return {
                'content': "I couldn't find destinations matching your preferences. Could you tell me more about what you're looking for?",
                'quick_replies': []
            }
        
        # Format recommendations
        response_text = "Based on your preferences, here are my top recommendations:\n\n"
        suggestions = []
        
        for i, rec in enumerate(recommendations[:3], 1):
            dest = rec['destination']
            reasons = ", ".join(rec['reasons'][:2])
            response_text += f"{i}. **{dest.name}, {dest.state}**\n   {reasons}\n\n"
            suggestions.append({
                'id': str(dest.id),
                'name': dest.name,
                'state': dest.state,
                'score': rec['score']
            })
        
        response_text += "Would you like to know more about any of these destinations?"
        
        return {
            'content': response_text,
            'suggestions': suggestions,
            'quick_replies': [
                {'text': 'Tell me more', 'value': 'more_info'},
                {'text': 'Create itinerary', 'value': 'create_itinerary'},
                {'text': 'Show more options', 'value': 'more_options'}
            ]
        }
    
    def handle_budget_query(self, message_text):
        """Handle budget-related queries"""
        if self.state.budget:
            budget = self.state.budget
            return {
                'content': f"Based on your budget of ₹{budget.get('amount', 'N/A')}, I can suggest destinations that match your price range. Would you like to see recommendations?",
                'quick_replies': [
                    {'text': 'Yes, show me', 'value': 'show_recommendations'},
                    {'text': 'Change budget', 'value': 'change_budget'}
                ]
            }
        
        return {
            'content': "What's your budget for this trip? You can tell me the total amount or select from these ranges:",
            'quick_replies': [
                {'text': 'Budget (Under ₹20k)', 'value': 'budget'},
                {'text': 'Mid-Range (₹20k-50k)', 'value': 'mid_range'},
                {'text': 'Luxury (₹50k+)', 'value': 'luxury'}
            ]
        }
    
    def handle_weather_query(self, message_text):
        """Handle weather queries"""
        return {
            'content': "I can check current weather conditions for your destination. Which place would you like weather information for?",
            'quick_replies': []
        }
    
    def handle_itinerary_request(self, message_text):
        """Handle itinerary creation requests"""
        missing_info = self._check_missing_info()
        
        if missing_info:
            return self._ask_for_missing_info(missing_info[0])
        
        return {
            'content': "Great! I'll create a personalized itinerary for you. Give me a moment to plan the perfect trip...",
            'quick_replies': []
        }
    
    def handle_travel_dates(self, message_text):
        """Handle travel date information"""
        if self.state.travel_dates:
            dates = self.state.travel_dates
            start = dates.get('start_date', 'Not set')
            end = dates.get('end_date', 'Not set')
            
            return {
                'content': f"Got it! You're planning to travel from {start} to {end}. What else would you like to know?",
                'quick_replies': [
                    {'text': 'Suggest destinations', 'value': 'suggest_destinations'},
                    {'text': 'Check weather', 'value': 'check_weather'}
                ]
            }
        
        return {
            'content': "When are you planning to travel? You can tell me specific dates or just the month.",
            'quick_replies': []
        }
    
    def handle_companion_info(self, message_text):
        """Handle companion information"""
        if self.state.companions:
            comp_type = self.state.companions.get('type', 'group')
            return {
                'content': f"Noted! You're traveling with {comp_type}. I'll suggest {comp_type}-friendly destinations.",
                'quick_replies': [
                    {'text': 'Show recommendations', 'value': 'show_recommendations'}
                ]
            }
        
        return {
            'content': "Who will you be traveling with?",
            'quick_replies': [
                {'text': 'Solo', 'value': 'solo'},
                {'text': 'Family', 'value': 'family'},
                {'text': 'Friends', 'value': 'friends'},
                {'text': 'Couple', 'value': 'couple'}
            ]
        }
    
    def handle_goodbye(self, message_text):
        """Handle goodbye messages"""
        farewells = [
            "Safe travels! Feel free to come back anytime you need travel advice.",
            "Have an amazing trip! Don't hesitate to reach out if you need anything.",
            "Goodbye! I'm here whenever you want to plan your next adventure."
        ]
        
        return {
            'content': random.choice(farewells),
            'quick_replies': []
        }
    
    def handle_general(self, message_text):
        """Handle general/unknown intents"""
        return {
            'content': "I'm here to help you plan your trip! You can ask me about destinations, create itineraries, check weather, or get travel recommendations. What would you like to do?",
            'quick_replies': [
                {'text': 'Suggest destinations', 'value': 'suggest_destinations'},
                {'text': 'Create itinerary', 'value': 'create_itinerary'},
                {'text': 'Check weather', 'value': 'check_weather'}
            ]
        }
    
    def _check_missing_info(self):
        """Check what information is missing"""
        missing = []
        
        if not self.state.travel_dates or not self.state.travel_dates.get('start_date'):
            missing.append('travel_dates')
        
        if not self.state.budget:
            missing.append('budget')
        
        if not self.state.companions:
            missing.append('companions')
        
        return missing
    
    def _ask_for_missing_info(self, info_type):
        """Generate question for missing information"""
        questions = {
            'travel_dates': {
                'content': "When are you planning to travel? Please tell me your travel dates.",
                'quick_replies': []
            },
            'budget': {
                'content': "What's your budget for this trip?",
                'quick_replies': [
                    {'text': 'Budget (Under ₹20k)', 'value': 'budget'},
                    {'text': 'Mid-Range (₹20k-50k)', 'value': 'mid_range'},
                    {'text': 'Luxury (₹50k+)', 'value': 'luxury'}
                ]
            },
            'companions': {
                'content': "Who will be traveling with you?",
                'quick_replies': [
                    {'text': 'Solo', 'value': 'solo'},
                    {'text': 'Family', 'value': 'family'},
                    {'text': 'Friends', 'value': 'friends'}
                ]
            }
        }
        
        return questions.get(info_type, self.handle_general(''))
    
    def _build_filters_from_context(self):
        """Build recommendation filters from conversation context"""
        filters = {}
        
        if self.state.budget:
            budget = self.state.budget
            if 'amount' in budget:
                filters['budget_min'] = 0
                filters['budget_max'] = budget['amount']
            elif 'category' in budget:
                from utils.constants import BUDGET_RANGES
                budget_range = BUDGET_RANGES.get(budget['category'], (0, float('inf')))
                filters['budget_min'] = budget_range[0]
                filters['budget_max'] = budget_range[1]
        
        if self.state.interests:
            filters['experience_types'] = self.state.interests
        
        if self.state.travel_dates and self.state.travel_dates.get('start_date'):
            from datetime import datetime
            start_date = datetime.strptime(self.state.travel_dates['start_date'], '%Y-%m-%d')
            filters['travel_month'] = start_date.strftime('%B')
        
        return filters