# chatbot/nlp_engine.py

import re
import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
import spacy
import google.generativeai as genai

logger = logging.getLogger(__name__)


class HybridNLPEngine:
    """
    Hybrid NLP Engine combining:
    1. spaCy for entity extraction (fast, local)
    2. Gemini API for intent classification and safety (free, accurate)
    3. Learning mechanism from user interactions
    """
    
    def __init__(self):
        # Initialize spaCy
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy loaded successfully")
        except OSError:
            logger.warning("⚠️ spaCy model not found. Run: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Initialize Gemini
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Gemini API configured")
        except Exception as e:
            logger.error(f"❌ Gemini initialization failed: {e}")
            self.gemini_model = None
        
        # Load learned patterns
        self.learned_patterns = self._load_learned_patterns()
        
        # Content safety categories
        self.safety_categories = {
            'vulgar': ['profanity', 'offensive', 'explicit'],
            'religious_extreme': ['extremist', 'hate speech', 'religious hatred'],
            'harmful': ['violence', 'illegal', 'dangerous'],
            'spam': ['promotional', 'advertisement', 'spam']
        }
    
    def _load_learned_patterns(self) -> Dict:
        """Load learned patterns from cache/database"""
        cached = cache.get('nlp_learned_patterns')
        if cached:
            return json.loads(cached)
        
        pattern_file = settings.BASE_DIR / 'data' / 'learned_patterns.json'
        if pattern_file.exists():
            with open(pattern_file, 'r') as f:
                return json.load(f)
        
        return {
            'intent_patterns': {},
            'entity_patterns': {},
            'phrase_mappings': {},
            'correction_history': []
        }
    
    def _save_learned_patterns(self):
        """Save learned patterns to cache"""
        cache.set('nlp_learned_patterns', json.dumps(self.learned_patterns), timeout=None)
        pattern_file = settings.BASE_DIR / 'data' / 'learned_patterns.json'
        pattern_file.parent.mkdir(exist_ok=True)
        with open(pattern_file, 'w') as f:
            json.dump(self.learned_patterns, f, indent=2)
    
    def process_message(self, message: str, user_id: str, session_context: Dict = None) -> Dict[str, Any]:
        """
        Main processing pipeline with REFERENCE DETECTION PRIORITY
        """
        message_clean = message.strip()
        
        # Step 1: Check cache
        cached_result = self._check_cache(message_clean)
        if cached_result:
            logger.info(f"Cache hit for: {message_clean[:50]}")
            return cached_result
        
        # Step 2: Extract entities
        entities = self._extract_entities_spacy(message_clean)
        
        # Step 3: PRIORITY CHECK - Reference Resolution
        # If user says "the first one", "tell me about it", etc.
        if session_context and session_context.get('current_destinations'):
            if self._is_reference_query(message_clean):
                logger.info(f"🎯 REFERENCE DETECTED: {message_clean}")
                return {
                    'message': message_clean,
                    'entities': entities,
                    'intent': 'reference',
                    'confidence': 0.95,
                    'is_safe': True,
                    'safety_issues': [],
                    'context_understanding': 'User is referring to previously shown destinations',
                    'suggested_response_type': 'informative',
                    'source': 'reference_detection',
                    'timestamp': datetime.now().isoformat()
                }
        
        # Step 4: Check learned patterns
        learned_intent = self._check_learned_patterns(message_clean)
        
        # Step 5: Gemini for intent + safety
        gemini_result = self._analyze_with_gemini(message_clean, entities, session_context)
        
        # Combine results
        final_result = {
            'message': message_clean,
            'entities': entities,
            'intent': learned_intent or gemini_result.get('intent', 'general'),
            'confidence': gemini_result.get('confidence', 0.5),
            'is_safe': gemini_result.get('is_safe', True),
            'safety_issues': gemini_result.get('safety_issues', []),
            'context_understanding': gemini_result.get('context_understanding', ''),
            'suggested_response_type': gemini_result.get('suggested_response_type', 'neutral'),
            'source': 'learned' if learned_intent else 'gemini',
            'timestamp': datetime.now().isoformat()
        }
        
        # Cache result
        self._cache_result(message_clean, final_result)
        
        return final_result
    
    def _is_reference_query(self, message: str) -> bool:
        """
        Detect if user is referring to previously shown results
        Returns True for: "the first one", "tell me about it", "that place", etc.
        """
        message_lower = message.lower().strip()
        
        # Reference patterns
        reference_patterns = [
            # Ordinal references
            r'\b(the )?(first|second|third|last|top)\s+(one|place|destination|option)\b',
            r'\b(1st|2nd|3rd)\s+(one|place|destination)?\b',
            
            # Pronoun references
            r'\b(tell me|more about|info about|details about|show me)\s+(the )?(first|second|it|that|this)\b',
            r'\b(it|that|this|these|those)\s+(one|place)?\b',
            
            # Selection phrases
            r'\b(which of|any of)\s+(these|those|them)\b',
            r'\b(pick|choose|select)\s+(the )?(first|second|one)\b',
            
            # Simple references
            r'^\s*(first|second|last|it|that)\s*$',  # Just "first" or "it"
            r'^\s*(tell me|more|details)\s+(about )?(first|second|it|that)\s*$',
        ]
        
        for pattern in reference_patterns:
            if re.search(pattern, message_lower):
                logger.info(f"✅ Reference pattern matched: {pattern}")
                return True
        
        return False


    def _extract_entities_spacy(self, message: str) -> Dict[str, Any]:
        """Extract entities using spaCy"""
        if not self.nlp:
            return self._fallback_entity_extraction(message)
        
        doc = self.nlp(message)
        
        entities = {
            'locations': [],
            'numbers': [],
            'dates': [],
            'money': [],
            'durations': [],
            'activities': [],
            'primary_activity': None,  # NEW: The main activity user is asking for
            'filter_mode': 'strict',    # NEW: strict or relaxed filtering
            'person_count': None
        }
        
        # Named Entity Recognition
        for ent in doc.ents:
            if ent.label_ in ['GPE', 'LOC', 'FAC']:  # Locations
                entities['locations'].append(ent.text)
            elif ent.label_ == 'MONEY':
                entities['money'].append(ent.text)
            elif ent.label_ == 'DATE':
                entities['dates'].append(ent.text)
            elif ent.label_ == 'CARDINAL':
                entities['numbers'].append(int(ent.text) if ent.text.isdigit() else ent.text)
        
        # Extract budget (rupees)
        budget_match = re.search(r'(\d+)k?\s*(budget|rupees|rs|inr)?', message.lower())
        if budget_match:
            amount = int(budget_match.group(1))
            if amount < 1000:
                amount *= 1000
            entities['budget'] = {'amount': amount, 'max': amount}
        
        # Extract duration
        duration_match = re.search(r'(\d+)\s*days?', message.lower())
        if duration_match:
            entities['durations'].append(int(duration_match.group(1)))
        
        # NEW: Improved activity extraction with PRIMARY activity detection
        activity_keywords = {
            'beach': ['beach', 'beaches', 'sea', 'ocean', 'coastal', 'seaside'],
            'mountain': ['mountain', 'mountains', 'hill', 'hills', 'peak', 'trekking', 'hiking','hilly'],
            'adventure': ['adventure', 'adventurous', 'rafting', 'paragliding', 'bungee'],
            'cultural': ['cultural', 'heritage', 'temple', 'temples', 'monument', 'monuments', 'historical', 'fort', 'forts'],
            'wildlife': ['wildlife', 'safari', 'animals', 'jungle', 'forest', 'national park'],
            'spiritual': ['spiritual', 'pilgrimage', 'religious', 'shrine', 'ashram'],
            'relaxation': ['relax', 'relaxing', 'peaceful', 'calm', 'wellness', 'spa', 'rejuvenate'],
            'food': ['food', 'culinary', 'cuisine', 'restaurant', 'street food'],
            'waterfall': ['waterfall', 'waterfalls', 'falls'],
            'lake': ['lake', 'lakes'],
        }
        
        message_lower = message.lower()
        matched_activities = []
        
        # Check each activity and record matches
        for activity, keywords in activity_keywords.items():
            for keyword in keywords:
                # Use word boundaries for better matching
                if re.search(r'\b' + re.escape(keyword) + r'\b', message_lower):
                    matched_activities.append(activity)
                    break  # Don't add same activity multiple times
        
        # Determine PRIMARY activity based on explicit mentions
        # Priority: If user says "show me beach destinations", "beach" is primary
        primary_activity_patterns = [
            (r'\b(show|find|search|looking for|want|suggest|recommend)\s+\w*\s*(beach|beaches)\s+(destination|place)', 'beach'),
            (r'\b(show|find|search|looking for|want|suggest|recommend)\s+\w*\s*(mountain|mountains|hill)\s+(destination|place)', 'mountain'),
            (r'\b(show|find|search|looking for|want|suggest|recommend)\s+\w*\s*(adventure|adventurous)\s+(destination|place)', 'adventure'),
            (r'\b(show|find|search|looking for|want|suggest|recommend)\s+\w*\s*(cultural|heritage)\s+(destination|place)', 'cultural'),
            (r'\b(show|find|search|looking for|want|suggest|recommend)\s+\w*\s*(wildlife|safari)\s+(destination|place)', 'wildlife'),
            (r'\b(show|find|search|looking for|want|suggest|recommend)\s+\w*\s*(spiritual|religious|pilgrimage)\s+(destination|place)', 'spiritual'),
            
            # Direct mentions
            (r'\b(beach|beaches)\s+(destination|place|location)', 'beach'),
            (r'\b(mountain|mountains)\s+(destination|place|location)', 'mountain'),
            (r'\b(adventure)\s+(destination|place|location)', 'adventure'),
            (r'\b(cultural|heritage)\s+(destination|place|location)', 'cultural'),
            (r'\b(waterfall|waterfalls)\s+(destination|place|location)', 'waterfall'),
        ]
        
        primary_detected = False
        for pattern, activity in primary_activity_patterns:
            if re.search(pattern, message_lower):
                entities['primary_activity'] = activity
                entities['filter_mode'] = 'strict'  # Use strict filtering
                primary_detected = True
                break
        
        # If no primary activity detected but activities were found
        if not primary_detected and matched_activities:
            # If only one activity matched, make it primary
            if len(matched_activities) == 1:
                entities['primary_activity'] = matched_activities[0]
                entities['filter_mode'] = 'strict'
            # If multiple activities, use relaxed mode
            else:
                entities['filter_mode'] = 'relaxed'
        
        # Set all matched activities
        entities['activities'] = list(set(matched_activities))  # Remove duplicates
        
        # Extract person count
        person_patterns = [
            r'(\d+)\s*(people|person|pax)',
            r'(solo|alone|myself)',
            r'(couple|two|2)',
            r'(family|group)'
        ]
        
        for pattern in person_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if 'solo' in match.group(0) or 'alone' in match.group(0):
                    entities['person_count'] = 1
                elif 'couple' in match.group(0) or 'two' in match.group(0):
                    entities['person_count'] = 2
                elif 'family' in match.group(0):
                    entities['person_count'] = 4
                elif match.group(1).isdigit():
                    entities['person_count'] = int(match.group(1))
                break
        
        return entities
    
    def _fallback_intent_classification(self, message: str, entities: Dict) -> Dict[str, Any]:
        """Fallback when Gemini unavailable - use rule-based classification"""
        message_lower = message.lower()
        
        # Rule-based intent detection
        intent = 'general'
        confidence = 0.6
        
        # REFERENCE - Check FIRST
        if self._is_reference_query(message):
            intent = 'reference'
            confidence = 0.95
        
        # GREETING - Must be at START of message or standalone
        elif any(message_lower.strip().startswith(word) or message_lower.strip() == word 
                for word in ['hi', 'hello', 'hey', 'namaste', 'good morning', 'good evening']):
            intent = 'greeting'
            confidence = 0.9
        
        # FAREWELL
        elif any(word in message_lower for word in ['bye', 'goodbye', 'later', 'see you']):
            intent = 'farewell'
            confidence = 0.9
        
        # DURATION (before SEARCH to prioritize constraint)
        elif (('days' in message_lower or 'for ' in message_lower) and 
            entities.get('durations') and 
            not any(word in message_lower for word in ['show', 'find', 'search'])):
            intent = 'duration'
            confidence = 0.85
        
        # BUDGET (before SEARCH to prioritize constraint)
        elif (('budget' in message_lower or 'under' in message_lower or 'within' in message_lower) and 
            (entities.get('budget') or re.search(r'\d+k?\s*(rupees|rs)?', message_lower))):
            intent = 'budget'
            confidence = 0.85
        
        # SEARCH - Must have search indicators + activities/locations
        elif (any(word in message_lower for word in ['show', 'find', 'search', 'looking for', 'give me', 'suggest']) and
            (entities.get('activities') or entities.get('locations') or 
            any(word in message_lower for word in ['destination', 'place', 'beach', 'mountain', 'hill']))):
            intent = 'search'
            confidence = 0.8
        
        # WEATHER
        elif any(word in message_lower for word in ['weather', 'temperature', 'climate', 'forecast']):
            intent = 'weather'
            confidence = 0.8
        
        # RECOMMENDATION
        elif any(word in message_lower for word in ['recommend', 'suggest']) and 'for me' in message_lower:
            intent = 'recommendation'
            confidence = 0.8
        
        # Basic safety check
        profanity_list = ['fuck', 'shit', 'damn', 'bitch', 'ass', 'bastard']
        is_safe = not any(word in message_lower for word in profanity_list)
        
        return {
            'intent': intent,
            'confidence': confidence,
            'is_safe': is_safe,
            'safety_issues': [] if is_safe else ['vulgar'],
            'context_understanding': f"Fallback detected as {intent} query",
            'suggested_response_type': 'informative' if is_safe else 'firm_decline'
        }
    
    def _analyze_with_gemini(self, message: str, entities: Dict, context: Dict = None) -> Dict[str, Any]:
        """
        Use Gemini to:
        1. Classify intent with high accuracy
        2. Check content safety
        3. Understand context and nuance
        """
        if not self.gemini_model:
            return self._fallback_intent_classification(message, entities)
        
        try:
            # Build prompt for Gemini
            prompt = self._build_gemini_prompt(message, entities, context)
            
            # Call Gemini API
            response = self.gemini_model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                # Fallback if not JSON
                logger.warning("Gemini didn't return JSON, parsing manually")
                result = self._parse_gemini_text_response(result_text)
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback_intent_classification(message, entities)
    
    def _build_gemini_prompt(self, message: str, entities: Dict, context: Dict = None) -> str:
        """
        Build structured prompt for Gemini with comprehensive intent detection
        Includes: attractions, restaurants, accommodations, and all other intents
        """
        
        context_info = ""
        if context:
            current_destinations = context.get('current_destinations', [])
            mentioned_destinations = context.get('mentioned_destinations', [])
            
            context_info = f"""
    Previous conversation context:
    - Current topic: {context.get('current_topic', 'None')}
    - Active search results: {len(current_destinations)} destinations shown
    - User was viewing: {len(current_destinations)} destinations
    - Recently discussed: {', '.join(mentioned_destinations[:3]) if mentioned_destinations else 'None'}
    - Last intent: {context.get('last_intent', 'None')}
    """
        
        prompt = f"""You are an AI assistant for a travel planning chatbot. Analyze this user message and return a JSON response.

    User message: "{message}"

    Extracted entities: {json.dumps(entities)}

    {context_info}

    CRITICAL INTENT DETECTION RULES (Priority Order):

    **TIER 1 - Reference & Conversation Flow:**
    1. "reference" = User referring to previous results (e.g., "the first one", "tell me about it", "that place", "show it")

    **TIER 2 - Progressive Filtering (when results exist):**
    2. "duration" = ONLY duration mentioned WITHOUT search words (e.g., "for 5 days", "7 days")
    3. "budget" = ONLY budget mentioned WITHOUT search words (e.g., "under 30k", "within budget")

    **TIER 3 - Destination-Specific Queries:**
    4. "attractions" = Things to do, places to visit, activities (e.g., "What can I do in Goa?", "Things to do", "Places to visit in Manali", "activities in Delhi")
    5. "restaurants" = Food, dining, where to eat (e.g., "Where to eat in Goa?", "Best restaurants", "food places", "good restaurants in Mumbai")
    6. "accommodations" = Hotels, stay, lodging (e.g., "Where to stay?", "Hotels in Manali", "Best places to stay", "accommodation in Jaipur")
    7. "weather" = Climate, temperature, forecast (e.g., "What's the weather?", "Will it rain?")
    8. "safety" = Safety concerns, is it safe (e.g., "Is Goa safe?", "Safety in Delhi")

    **TIER 4 - Search & Discovery:**
    9. "search" = Looking for NEW destinations (e.g., "show me beach places", "find mountain destinations")
    10. "recommendation" = Personalized suggestions (e.g., "recommend destinations for me", "suggest places")

    **TIER 5 - Planning & Logistics:**
    11. "trip_planning" = Itinerary, planning (e.g., "Plan a trip to Goa", "Create itinerary")
    12. "bookmark" = Save, wishlist (e.g., "Save this destination", "Add to wishlist")
    13. "more_info" = General destination information (e.g., "Tell me about Goa", "More about Kashmir")

    **TIER 6 - Conversation:**
    14. "greeting" = Hi, hello, hey
    15. "farewell" = Bye, goodbye, thanks

    **TIER 7 - Safety:**
    16. "inappropriate" = Unsafe, vulgar, harmful content

    CRITICAL DISTINCTION EXAMPLES:
    ✓ "Tell me about the first one" → reference (referring to previous result)
    ✓ "For 5 days" → duration (just constraint, no search)
    ✓ "Under 30k budget" → budget (just constraint, no search)
    ✓ "Show me beach destinations" → search (new search)
    ✓ "For 5 days beach trip" → search (has search intent, not just constraint)
    ✓ "What can I do in Goa?" → attractions (asking about activities)
    ✓ "Where to eat in Manali?" → restaurants (asking about food)
    ✓ "Hotels in Jaipur" → accommodations (asking about stay)
    ✓ "Tell me about Goa" → more_info (general information, no specific category)

    **Location Detection:**
    - If message contains a specific location + activity question → Use specific intent
    - "Things to do in Goa" → attractions
    - "Restaurants in Mumbai" → restaurants
    - "Hotels in Delhi" → accommodations
    - If message is just "Tell me about [Place]" → more_info

    Return ONLY valid JSON in this exact format:
    {{
    "intent": "reference|duration|budget|attractions|restaurants|accommodations|weather|safety|search|recommendation|trip_planning|bookmark|more_info|greeting|farewell|inappropriate|general",
    "confidence": 0.95,
    "is_safe": true,
    "safety_issues": [],
    "context_understanding": "Brief explanation of what user wants",
    "suggested_response_type": "informative",
    "reasoning": "Why you chose this intent (1-2 sentences)"
    }}

    **Content Safety Guidelines:**
    - Mark as "inappropriate" if: profanity, hate speech, sexual content, violence, illegal activities
    - Safety issues can be: "vulgar", "religious_extreme", "harmful", "spam", "offensive"
    - Set is_safe to false if ANY safety issue detected

    **Intent Priority (Check in this order):**
    1. Reference → Duration/Budget → Attractions/Restaurants/Accommodations
    2. Weather/Safety → Search/Recommendation
    3. Trip Planning/Bookmark/More Info → Greeting/Farewell
    4. General (fallback)

    Response MUST be valid JSON only, no other text."""

        return prompt
    
    def _parse_gemini_text_response(self, text: str) -> Dict[str, Any]:
        """Parse non-JSON Gemini response"""
        # Fallback parser
        result = {
            'intent': 'general',
            'confidence': 0.5,
            'is_safe': True,
            'safety_issues': [],
            'context_understanding': text[:100],
            'suggested_response_type': 'informative'
        }
        
        # Try to extract intent from text
        text_lower = text.lower()
        if 'inappropriate' in text_lower or 'unsafe' in text_lower:
            result['intent'] = 'inappropriate'
            result['is_safe'] = False
            result['safety_issues'] = ['content_violation']
        elif 'search' in text_lower or 'destination' in text_lower:
            result['intent'] = 'search'
        elif 'budget' in text_lower:
            result['intent'] = 'budget'
        
        return result
    
    def _fallback_intent_classification(self, message: str, entities: Dict) -> Dict[str, Any]:
        """
        Fallback when Gemini unavailable - comprehensive rule-based classification
        Includes all intents with proper priority ordering
        """
        message_lower = message.lower().strip()
        
        intent = 'general'
        confidence = 0.6
        
        # ============================================================
        # TIER 1: REFERENCE (if context exists, check in calling function)
        # ============================================================
        if self._is_reference_query(message):
            intent = 'reference'
            confidence = 0.95
        
        # ============================================================
        # TIER 2: CONVERSATION FLOW
        # ============================================================
        # GREETING - Must be at START of message
        elif any(message_lower.startswith(word) or message_lower == word 
                for word in ['hi', 'hello', 'hey', 'namaste', 'good morning', 'good evening', 'greetings']):
            intent = 'greeting'
            confidence = 0.95
        
        # FAREWELL
        elif any(word in message_lower for word in ['bye', 'goodbye', 'see you later', 'thanks', 'thank you']):
            intent = 'farewell'
            confidence = 0.9
        
        # ============================================================
        # TIER 3: DESTINATION-SPECIFIC QUERIES (High Priority)
        # ============================================================
        
        # ATTRACTIONS - Things to do, places to visit
        elif any(phrase in message_lower for phrase in [
            'things to do', 'what can i do', 'what to do', 'what should i do',
            'places to visit', 'places to see', 'what to see', 'places to go',
            'activities', 'attractions', 'sightseeing', 'tourist places',
            'visit in', 'see in', 'do in', 'explore in',
            'famous places', 'must visit', 'top attractions'
        ]):
            intent = 'attractions'
            confidence = 0.9
        
        # RESTAURANTS - Where to eat, food places
        elif any(phrase in message_lower for phrase in [
            'where to eat', 'where can i eat', 'where should i eat',
            'restaurants', 'restaurant in', 'food', 'dining',
            'best food', 'eat in', 'cuisine', 'places to eat',
            'good food', 'food places', 'cafes', 'cafe in',
            'local food', 'street food', 'famous food'
        ]):
            intent = 'restaurants'
            confidence = 0.9
        
        # ACCOMMODATIONS - Where to stay, hotels
        elif any(phrase in message_lower for phrase in [
            'where to stay', 'where can i stay', 'where should i stay',
            'hotels', 'hotel in', 'accommodation', 'accommodations',
            'lodging', 'stay in', 'places to stay',
            'guest house', 'guesthouse', 'resort', 'resorts',
            'hostel', 'hostels', 'booking', 'best hotels'
        ]):
            intent = 'accommodations'
            confidence = 0.9
        
        # ============================================================
        # TIER 4: PROGRESSIVE FILTERING (When adding constraints)
        # ============================================================
        
        # DURATION (before SEARCH to prioritize constraint)
        elif (('days' in message_lower or 'for ' in message_lower or 'day' in message_lower) and 
            entities.get('durations') and 
            not any(word in message_lower for word in ['show', 'find', 'search', 'looking for'])):
            intent = 'duration'
            confidence = 0.85
        
        # BUDGET (before SEARCH to prioritize constraint)
        elif (('budget' in message_lower or 'under' in message_lower or 'within' in message_lower or 
            'cheap' in message_lower or 'affordable' in message_lower) and 
            (entities.get('budget') or re.search(r'\d+k?\s*(rupees|rs|inr)?', message_lower)) and
            not any(word in message_lower for word in ['show', 'find', 'search'])):
            intent = 'budget'
            confidence = 0.85
        
        # ============================================================
        # TIER 5: SEARCH & DISCOVERY
        # ============================================================
        
        # SEARCH - Must have search indicators + activities/locations
        elif (any(word in message_lower for word in [
            'show', 'find', 'search', 'looking for', 'give me', 'suggest', 'list'
        ]) and (
            entities.get('activities') or 
            entities.get('locations') or 
            any(word in message_lower for word in [
                'destination', 'destinations', 'place', 'places',
                'beach', 'beaches', 'mountain', 'mountains', 'hill', 'hills'
            ])
        )):
            intent = 'search'
            confidence = 0.85
        
        # RECOMMENDATION
        elif any(phrase in message_lower for phrase in [
            'recommend', 'recommendations', 'suggest', 'suggestions',
            'what do you recommend', 'what would you suggest'
        ]) and any(word in message_lower for word in ['for me', 'me some', 'to me']):
            intent = 'recommendation'
            confidence = 0.85
        
        # ============================================================
        # TIER 6: INFORMATION & QUERIES
        # ============================================================
        
        # WEATHER
        elif any(word in message_lower for word in [
            'weather', 'temperature', 'climate', 'forecast',
            'rain', 'sunny', 'cold', 'hot', 'warm'
        ]):
            intent = 'weather'
            confidence = 0.85
        
        # SAFETY
        elif any(phrase in message_lower for phrase in [
            'is it safe', 'safe to visit', 'safety', 'is safe',
            'safe to travel', 'how safe'
        ]):
            intent = 'safety'
            confidence = 0.85
        
        # MORE INFO (general information about a destination)
        elif any(phrase in message_lower for phrase in [
            'tell me about', 'tell me more about', 'more about',
            'information about', 'details about', 'know about',
            'what is', 'what\'s', 'describe'
        ]) and not any(phrase in message_lower for phrase in [
            'things to do', 'where to eat', 'where to stay'
        ]):
            intent = 'more_info'
            confidence = 0.85
        
        # ============================================================
        # TIER 7: PLANNING & ACTIONS
        # ============================================================
        
        # TRIP PLANNING
        elif any(phrase in message_lower for phrase in [
            'plan a trip', 'plan my trip', 'create itinerary',
            'itinerary', 'schedule', 'trip plan'
        ]):
            intent = 'trip_planning'
            confidence = 0.85
        
        # BOOKMARK
        elif any(phrase in message_lower for phrase in [
            'save', 'bookmark', 'add to wishlist', 'wishlist',
            'save this', 'remember this'
        ]):
            intent = 'bookmark'
            confidence = 0.85
        
        # ============================================================
        # TIER 8: SAFETY CHECK
        # ============================================================
        
        # Basic profanity/safety check
        profanity_list = ['fuck', 'shit', 'damn', 'bitch', 'ass', 'bastard', 'hell']
        is_safe = not any(word in message_lower for word in profanity_list)
        
        if not is_safe:
            intent = 'inappropriate'
            confidence = 0.95
        
        return {
            'intent': intent,
            'confidence': confidence,
            'is_safe': is_safe,
            'safety_issues': [] if is_safe else ['vulgar'],
            'context_understanding': f"Rule-based classification detected as {intent} query",
            'suggested_response_type': 'informative' if is_safe else 'firm_decline'
        }
    
    def _check_learned_patterns(self, message: str) -> Optional[str]:
        """Check if message matches learned patterns"""
        message_lower = message.lower()
        
        # Check phrase mappings
        phrase_mappings = self.learned_patterns.get('phrase_mappings', {})
        for known_phrase, intent in phrase_mappings.items():
            if self._fuzzy_match(message_lower, known_phrase, threshold=0.85):
                logger.info(f"Matched learned pattern: {known_phrase} -> {intent}")
                return intent
        
        return None
    
    def _fuzzy_match(self, str1: str, str2: str, threshold: float = 0.8) -> bool:
        """Check if two strings match with fuzzy logic"""
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, str1, str2).ratio()
        return ratio >= threshold
    
    def learn_from_interaction(self, message: str, detected_intent: str, 
                               user_feedback: Optional[str] = None, 
                               correct_intent: Optional[str] = None):
        """
        Learning mechanism: Update patterns based on user interactions
        """
        message_clean = message.lower().strip()
        
        # If user provided correction
        if correct_intent and correct_intent != detected_intent:
            logger.info(f"Learning: '{message_clean}' -> {correct_intent} (was {detected_intent})")
            
            # Add to phrase mappings
            phrase_mappings = self.learned_patterns.get('phrase_mappings', {})
            phrase_mappings[message_clean] = correct_intent
            self.learned_patterns['phrase_mappings'] = phrase_mappings
            
            # Add to correction history
            correction_history = self.learned_patterns.get('correction_history', [])
            correction_history.append({
                'message': message_clean,
                'wrong_intent': detected_intent,
                'correct_intent': correct_intent,
                'timestamp': datetime.now().isoformat()
            })
            self.learned_patterns['correction_history'] = correction_history[-100:]  # Keep last 100
            
            # Save patterns
            self._save_learned_patterns()
        
        # If positive feedback (implicit learning)
        elif user_feedback == 'positive':
            # Reinforce current pattern
            phrase_mappings = self.learned_patterns.get('phrase_mappings', {})
            phrase_mappings[message_clean] = detected_intent
            self.learned_patterns['phrase_mappings'] = phrase_mappings
            self._save_learned_patterns()
    
    def _check_cache(self, message: str) -> Optional[Dict]:
        """Check if similar query was processed recently"""
        cache_key = f"nlp_cache:{hash(message.lower())}"
        return cache.get(cache_key)
    
    def _cache_result(self, message: str, result: Dict):
        """Cache processing result for 1 hour"""
        cache_key = f"nlp_cache:{hash(message.lower())}"
        cache.set(cache_key, result, timeout=3600)
    
    def handle_inappropriate_content(self, message: str, safety_issues: List[str]) -> Dict[str, str]:
        """
        Generate appropriate response for inappropriate content
        """
        if 'vulgar' in safety_issues:
            return {
                'message': "I noticed some inappropriate language. Let's keep our conversation respectful! 😊\n\n"
                          "How can I help you plan your trip?",
                'tone': 'gentle_redirect'
            }
        
        elif 'religious_extreme' in safety_issues:
            return {
                'message': "I'm here to help you discover amazing travel destinations! 🌍\n\n"
                          "I focus on travel planning and can't engage in religious discussions. "
                          "What kind of places would you like to explore?",
                'tone': 'firm_redirect'
            }
        
        elif 'harmful' in safety_issues:
            return {
                'message': "I can't assist with that request. I'm designed to help with travel planning. 🛡️\n\n"
                          "Would you like to explore some amazing destinations instead?",
                'tone': 'firm_decline'
            }
        
        elif 'spam' in safety_issues:
            return {
                'message': "I'm a travel assistant focused on helping you plan trips! 🎒\n\n"
                          "What destinations are you interested in?",
                'tone': 'redirect'
            }
        
        else:
            return {
                'message': "Let's keep our conversation focused on travel planning! 😊\n\n"
                          "What kind of destinations interest you?",
                'tone': 'gentle_redirect'
            }


# Singleton instance
_nlp_engine_instance = None

def get_nlp_engine() -> HybridNLPEngine:
    """Get or create NLP engine singleton"""
    global _nlp_engine_instance
    if _nlp_engine_instance is None:
        _nlp_engine_instance = HybridNLPEngine()
    return _nlp_engine_instance