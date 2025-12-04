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
import os

logger = logging.getLogger(__name__)

# Suppress GRPC warnings
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'


class HybridNLPEngine:
    """
    Hybrid NLP Engine combining:
    1. spaCy for entity extraction (fast, local)
    2. Gemini API for intent classification and safety (free, accurate)
    3. Learning mechanism from user interactions
    4. Location context memory for smart reference resolution
    """
    
    def __init__(self):
        # Initialize spaCy
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✓ spaCy loaded successfully")
        except OSError:
            logger.warning("⚠️ spaCy model not found. Run: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Initialize Gemini with proper error handling
        self.gemini_model = None
        try:
            api_key = getattr(settings, 'GEMINI_API_KEY', None)
            if api_key and api_key != 'your-api-key-here':
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel(
                    'gemini-2.5-flash',  # Using latest stable model
                    generation_config={
                        'temperature': 0.7,
                        'top_p': 0.95,
                        'top_k': 40,
                        'max_output_tokens': 1024,
                    }
                )
                logger.info("✓ Gemini API configured successfully")
            else:
                logger.warning("⚠️ GEMINI_API_KEY not configured. Using fallback classification.")
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
            try:
                with open(pattern_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading patterns: {e}")
        
        return {
            'intent_patterns': {},
            'entity_patterns': {},
            'phrase_mappings': {},
            'correction_history': []
        }
    
    def _save_learned_patterns(self):
        """Save learned patterns to cache"""
        try:
            cache.set('nlp_learned_patterns', json.dumps(self.learned_patterns), timeout=None)
            pattern_file = settings.BASE_DIR / 'data' / 'learned_patterns.json'
            pattern_file.parent.mkdir(exist_ok=True)
            with open(pattern_file, 'w') as f:
                json.dump(self.learned_patterns, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving patterns: {e}")

    def _detect_tell_me_about_query(self, message: str, entities: Dict) -> Optional[Dict]:
        """
        Detect "Tell me about X" queries where X is a destination
        Examples:
        - "Tell me about Goa"
        - "Tell me more about Manali"
        - "What about Kerala?"
        - "Info about Delhi"
        """
        message_lower = message.lower().strip()
        
        # Patterns for "tell me about" queries
        tell_me_patterns = [
            r'\b(tell me|tell me more|info|information|details|describe)\s+(about|on)\s+(\w+)',
            r'\bwhat about\s+(\w+)',
            r'\bhow about\s+(\w+)',
            r'\b(\w+)\s+info\b',
        ]
        
        location_mentioned = None
        
        # Check if it matches any pattern
        for pattern in tell_me_patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Extract the location name (last captured group)
                groups = match.groups()
                potential_location = groups[-1]
                
                # Check if this is a valid destination name
                from destinations.models import Destination
                all_destinations = cache.get('all_destination_names_lower')
                if not all_destinations:
                    all_destinations = {d.lower(): d for d in Destination.objects.values_list('name', flat=True)}
                    cache.set('all_destination_names_lower', all_destinations, 3600)
                
                # Check if mentioned word is a destination
                for dest_lower, dest_name in all_destinations.items():
                    if potential_location in dest_lower or dest_lower in potential_location:
                        location_mentioned = dest_name
                        break
                
                if location_mentioned:
                    break
        
        # Also check entities for location
        if not location_mentioned and entities.get('locations'):
            location_mentioned = entities['locations'][0]
        
        # If we found a location, return more_info intent
        if location_mentioned:
            return {
                'message': message,
                'entities': {**entities, 'location': {'name': location_mentioned}},
                'intent': 'more_info',
                'confidence': 0.95,
                'is_safe': True,
                'safety_issues': [],
                'context_understanding': f"User asking for information about {location_mentioned}",
                'suggested_response_type': 'informative',
                'source': 'tell_me_about_detection',
                'location_context': {
                    'name': location_mentioned,
                    'source': 'direct_mention',
                    'confidence': 0.95
                },
                'timestamp': datetime.now().isoformat()
            }
        
        return None

    
    def process_message(self, message: str, user_id: str, session_context: Dict = None) -> Dict[str, Any]:
        """
        Main processing pipeline with SMART REFERENCE DETECTION
        Priority: Location Context > Result References > General Queries
        """
        message_clean = message.strip()
        
        # Step 1: Check cache
        cached_result = self._check_cache(message_clean, str(session_context))
        if cached_result:
            logger.info(f"✓ Cache hit for: {message_clean[:50]}")
            return cached_result
        
        # Step 2: Extract entities with LOCATION MEMORY
        entities = self._extract_entities_spacy(message_clean, session_context)

        tell_me_result = self._detect_tell_me_about_query(message_clean, entities)
        if tell_me_result:
            logger.info(f"🎯 TELL ME ABOUT QUERY: {tell_me_result.get('location_context', {}).get('name')}")
            return tell_me_result
        
        # Step 3: PRIORITY 1 - Location-specific query detection
        # If user asks "restaurants in X" or mentions a location they discussed before
        location_specific_intent = self._detect_location_specific_intent(
            message_clean, entities, session_context
        )
        
        if location_specific_intent:
            logger.info(f"🎯 LOCATION-SPECIFIC QUERY: {location_specific_intent['intent']} for {location_specific_intent.get('location')}")
            return location_specific_intent
        
        # Step 4: PRIORITY 2 - Reference to previous results
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
        
        # Step 5: Check learned patterns
        learned_intent = self._check_learned_patterns(message_clean)
        
        # Step 6: Gemini for intent + safety (with improved error handling)
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
            'source': 'learned' if learned_intent else gemini_result.get('source', 'gemini'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Cache result
        self._cache_result(message_clean, final_result, str(session_context))
        
        return final_result
    
    def _detect_location_specific_intent(self, message: str, entities: Dict, 
                                         session_context: Dict = None) -> Optional[Dict]:
        """
        NEW: Detect location-specific queries like:
        - "restaurants in Goa"
        - "where to stay" (when Goa was just discussed)
        - "things to do there" (referring to last mentioned place)
        """
        message_lower = message.lower().strip()
        
        # Extract mentioned location from message OR context
        mentioned_location = self._extract_location_from_context(message, entities, session_context)
        
        if not mentioned_location:
            return None
        
        # Check for specific intent patterns with location
        intent_patterns = {
            'attractions': [
                r'\b(things to do|what to do|activities|attractions|places to visit|sightseeing|tourist places|visit)\b',
                r'\b(see|explore|check out)\b(?!.*\bshow\b)',  # "what to see" but not "show me"
            ],
            'restaurants': [
                r'\b(restaurant|restaurants|food|eat|eating|dining|cuisine|cafes?|places to eat|where to eat|best food)\b',
            ],
            'accommodations': [
                r'\b(hotel|hotels|stay|staying|accommodation|lodging|where to stay|places to stay|guest house|resort|hostel)\b',
            ],
            'weather': [
                r'\b(weather|temperature|climate|forecast|rain|sunny|cold|hot)\b',
            ],
            'safety': [
                r'\b(safe|safety|secure|dangerous|is it safe)\b',
            ],
        }
        
        detected_intent = None
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    detected_intent = intent
                    break
            if detected_intent:
                break
        
        if detected_intent:
            return {
                'message': message,
                'entities': {**entities, 'location': mentioned_location},
                'intent': detected_intent,
                'confidence': 0.95,
                'is_safe': True,
                'safety_issues': [],
                'context_understanding': f"User asking about {detected_intent} in {mentioned_location['name']}",
                'suggested_response_type': 'informative',
                'source': 'location_specific_detection',
                'location_context': mentioned_location,
                'timestamp': datetime.now().isoformat()
            }
        
        return None
    
    def _extract_location_from_context(self, message: str, entities: Dict, 
                                       session_context: Dict = None) -> Optional[Dict]:
        """
        Extract location from:
        1. Direct mention in message ("restaurants in Goa")
        2. Session context (last discussed location)
        3. Reference words (there, it, that place)
        """
        message_lower = message.lower()
        
        # Priority 1: Direct location mention in message
        if entities.get('locations'):
            location_name = entities['locations'][0]
            return {
                'name': location_name,
                'source': 'direct_mention',
                'confidence': 0.95
            }
        
        # Priority 2: Check for location names in message (fuzzy matching)
        # This catches cases like "Manali" even if spaCy missed it
        from destinations.models import Destination
        all_destinations = cache.get('all_destination_names')
        if not all_destinations:
            all_destinations = list(Destination.objects.values_list('name', flat=True))
            cache.set('all_destination_names', all_destinations, 3600)
        
        for dest_name in all_destinations:
            if dest_name.lower() in message_lower:
                return {
                    'name': dest_name,
                    'source': 'fuzzy_match',
                    'confidence': 0.90
                }
        
        # Priority 3: Reference words pointing to context
        reference_words = ['there', 'it', 'that place', 'this place', 'the place']
        has_reference = any(word in message_lower for word in reference_words)
        
        if has_reference and session_context:
            last_location = session_context.get('last_discussed_location')
            if last_location:
                return {
                    'name': last_location.get('name'),
                    'id': last_location.get('id'),
                    'source': 'context_reference',
                    'confidence': 0.85
                }
        
        # Priority 4: Last discussed location in context (implicit)
        if session_context:
            last_location = session_context.get('last_discussed_location')
            
            # Only use context if message is asking location-specific question
            location_specific_words = [
                'restaurant', 'hotel', 'stay', 'eat', 'food', 'accommodation',
                'things to do', 'activities', 'attractions', 'weather', 'safe'
            ]
            
            is_location_question = any(word in message_lower for word in location_specific_words)
            
            if last_location and is_location_question:
                # Check if it's NOT a new search query
                search_indicators = ['show', 'find', 'search', 'looking for', 'give me', 'suggest']
                is_new_search = any(word in message_lower for word in search_indicators)
                
                if not is_new_search:
                    return {
                        'name': last_location.get('name'),
                        'id': last_location.get('id'),
                        'source': 'implicit_context',
                        'confidence': 0.75
                    }
        
        return None
    
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
            r'^\s*(it|that|this)\b',  # Just "it", "that", "this" at start
            
            # Selection phrases
            r'\b(which of|any of)\s+(these|those|them)\b',
            r'\b(pick|choose|select)\s+(the )?(first|second|one)\b',
            
            # Simple references
            r'^\s*(first|second|last)\s*$',  # Just "first" or "second"
            r'^\s*(tell me|more|details)\s+(about )?(first|second|it|that)\s*$',
        ]
        
        for pattern in reference_patterns:
            if re.search(pattern, message_lower):
                logger.info(f"✅ Reference pattern matched: {pattern}")
                return True
        
        return False

    def _extract_entities_spacy(self, message: str, session_context: Dict = None) -> Dict[str, Any]:
        """Extract entities using spaCy with improved location detection"""
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
            'primary_activity': None,
            'filter_mode': 'strict',
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
                if ent.text.isdigit():
                    entities['numbers'].append(int(ent.text))
        
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
        
        # Activity extraction (same as before)
        activity_keywords = {
            'beach': ['beach', 'beaches', 'sea', 'ocean', 'coastal', 'seaside'],
            'mountain': ['mountain', 'mountains', 'hill', 'hills', 'peak', 'trekking', 'hiking', 'hilly'],
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
        
        for activity, keywords in activity_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', message_lower):
                    matched_activities.append(activity)
                    break
        
        entities['activities'] = list(set(matched_activities))
        
        # Extract person count
        person_patterns = [
            (r'(\d+)\s*(people|person|pax)', lambda m: int(m.group(1))),
            (r'(solo|alone|myself)', lambda m: 1),
            (r'(couple|two|2)', lambda m: 2),
            (r'(family|group)', lambda m: 4)
        ]
        
        for pattern, extractor in person_patterns:
            match = re.search(pattern, message_lower)
            if match:
                entities['person_count'] = extractor(match)
                break
        
        return entities
    
    def _fallback_entity_extraction(self, message: str) -> Dict[str, Any]:
        """Fallback entity extraction when spaCy unavailable"""
        entities = {
            'locations': [],
            'activities': [],
            'budget': None,
            'durations': [],
            'person_count': None
        }
        
        # Simple regex-based extraction
        budget_match = re.search(r'(\d+)k?', message.lower())
        if budget_match:
            amount = int(budget_match.group(1))
            if amount < 1000:
                amount *= 1000
            entities['budget'] = {'amount': amount}
        
        return entities
    
    def _analyze_with_gemini(self, message: str, entities: Dict, context: Dict = None) -> Dict[str, Any]:
        """
        Use Gemini with ROBUST error handling and JSON parsing
        """
        if not self.gemini_model:
            logger.info("Gemini unavailable, using fallback classification")
            return self._fallback_intent_classification(message, entities)
        
        try:
            # Build prompt
            prompt = self._build_gemini_prompt(message, entities, context)
            
            # Call Gemini API with timeout
            response = self.gemini_model.generate_content(
                prompt,
                request_options={'timeout': 10}  # 10 second timeout
            )
            
            if not response or not hasattr(response, 'text'):
                logger.warning("Gemini returned empty response")
                return self._fallback_intent_classification(message, entities)
            
            result_text = response.text.strip()
            
            # Try to parse JSON
            result = self._parse_gemini_response(result_text)
            result['source'] = 'gemini'
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return self._fallback_intent_classification(message, entities)
    
    def _parse_gemini_response(self, text: str) -> Dict[str, Any]:
        """
        ROBUST JSON parsing with multiple fallback strategies
        """
        # Strategy 1: Direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract JSON from markdown code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Extract any JSON object from text
        json_match = re.search(r'\{[^{}]*"intent"[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Strategy 4: Manual parsing from text
        logger.warning(f"⚠️ Gemini didn't return valid JSON, parsing manually from: {text[:200]}")
        return self._manual_parse_gemini_text(text)
    
    def _manual_parse_gemini_text(self, text: str) -> Dict[str, Any]:
        """
        Manually extract intent and other fields from Gemini's text response
        """
        text_lower = text.lower()
        
        # Extract intent
        intent = 'general'
        intent_match = re.search(r'"intent":\s*"([^"]+)"', text)
        if intent_match:
            intent = intent_match.group(1)
        else:
            # Fallback: look for intent keywords in text
            intent_keywords = {
                'inappropriate': ['inappropriate', 'unsafe', 'vulgar'],
                'search': ['search', 'looking for', 'find destinations'],
                'attractions': ['attractions', 'things to do'],
                'restaurants': ['restaurants', 'food', 'dining'],
                'accommodations': ['accommodation', 'hotels', 'stay'],
                'weather': ['weather', 'climate'],
                'budget': ['budget', 'cost'],
                'greeting': ['greeting', 'hello']
            }
            
            for intent_type, keywords in intent_keywords.items():
                if any(kw in text_lower for kw in keywords):
                    intent = intent_type
                    break
        
        # Extract confidence
        confidence = 0.6
        conf_match = re.search(r'"confidence":\s*([0-9.]+)', text)
        if conf_match:
            confidence = float(conf_match.group(1))
        
        # Extract safety
        is_safe = 'unsafe' not in text_lower and 'inappropriate' not in text_lower
        
        return {
            'intent': intent,
            'confidence': confidence,
            'is_safe': is_safe,
            'safety_issues': [] if is_safe else ['content_violation'],
            'context_understanding': text[:150],
            'suggested_response_type': 'informative' if is_safe else 'firm_decline'
        }
    
    def _build_gemini_prompt(self, message: str, entities: Dict, context: Dict = None) -> str:
        """Build structured prompt for Gemini"""
        
        context_info = ""
        if context:
            current_destinations = context.get('current_destinations', [])
            last_location = context.get('last_discussed_location')
            
            context_info = f"""
Previous conversation context:
- Last discussed location: {last_location.get('name') if last_location else 'None'}
- Current search results: {len(current_destinations)} destinations shown
- Last intent: {context.get('last_intent', 'None')}
"""
        
        prompt = f"""You are an AI assistant for a travel planning chatbot. Analyze this user message and return ONLY a valid JSON object.

User message: "{message}"
Extracted entities: {json.dumps(entities)}
{context_info}

CRITICAL RULES:
1. Return ONLY valid JSON, no other text
2. No markdown, no code blocks, just pure JSON
3. Intent priority: reference > location-specific > constraints > search > general

Available intents:
- reference: User referring to previous results ("the first one", "tell me about it")
- attractions: Things to do, places to visit
- restaurants: Where to eat, food places
- accommodations: Hotels, where to stay
- weather: Weather/climate queries
- safety: Safety concerns
- search: Looking for NEW destinations
- duration: Just mentioning duration constraint
- budget: Just mentioning budget constraint
- greeting: Hi, hello
- farewell: Bye, thanks
- general: Everything else

Return this EXACT format:
{{"intent":"search","confidence":0.9,"is_safe":true,"safety_issues":[],"context_understanding":"Brief explanation","suggested_response_type":"informative"}}"""

        return prompt
    
    def _fallback_intent_classification(self, message: str, entities: Dict) -> Dict[str, Any]:
        """
        Comprehensive fallback when Gemini unavailable
        """
        message_lower = message.lower().strip()
        
        intent = 'general'
        confidence = 0.6
        
        # Reference check
        if self._is_reference_query(message):
            intent = 'reference'
            confidence = 0.95
        
        # Greeting
        elif any(message_lower.startswith(word) or message_lower == word 
                for word in ['hi', 'hello', 'hey', 'namaste']):
            intent = 'greeting'
            confidence = 0.95
        
        # Attractions
        elif any(phrase in message_lower for phrase in [
            'things to do', 'what to do', 'places to visit', 'activities', 'attractions'
        ]):
            intent = 'attractions'
            confidence = 0.9
        
        # Restaurants
        elif any(phrase in message_lower for phrase in [
            'restaurant', 'where to eat', 'food', 'dining', 'eat in'
        ]):
            intent = 'restaurants'
            confidence = 0.9
        
        # Accommodations
        elif any(phrase in message_lower for phrase in [
            'hotel', 'where to stay', 'accommodation', 'stay in', 'lodging'
        ]):
            intent = 'accommodations'
            confidence = 0.9
        
        # Search
        elif any(word in message_lower for word in ['show', 'find', 'search', 'looking for']):
            intent = 'search'
            confidence = 0.85
        
        # Safety check
        profanity_list = ['fuck', 'shit', 'damn', 'bitch']
        is_safe = not any(word in message_lower for word in profanity_list)
        
        if not is_safe:
            intent = 'inappropriate'
            confidence = 0.95
        
        return {
            'intent': intent,
            'confidence': confidence,
            'is_safe': is_safe,
            'safety_issues': [] if is_safe else ['vulgar'],
            'context_understanding': f"Fallback: detected as {intent}",
            'suggested_response_type': 'informative' if is_safe else 'firm_decline',
            'source': 'fallback'
        }
    
    def _check_learned_patterns(self, message: str) -> Optional[str]:
        """Check if message matches learned patterns"""
        message_lower = message.lower()
        
        phrase_mappings = self.learned_patterns.get('phrase_mappings', {})
        for known_phrase, intent in phrase_mappings.items():
            if self._fuzzy_match(message_lower, known_phrase, threshold=0.85):
                logger.info(f"✓ Matched learned pattern: {known_phrase} -> {intent}")
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
        """Learning mechanism: Update patterns based on user interactions"""
        message_clean = message.lower().strip()
        
        if correct_intent and correct_intent != detected_intent:
            logger.info(f"📚 Learning: '{message_clean}' -> {correct_intent} (was {detected_intent})")
            
            phrase_mappings = self.learned_patterns.get('phrase_mappings', {})
            phrase_mappings[message_clean] = correct_intent
            self.learned_patterns['phrase_mappings'] = phrase_mappings
            
            correction_history = self.learned_patterns.get('correction_history', [])
            correction_history.append({
                'message': message_clean,
                'wrong_intent': detected_intent,
                'correct_intent': correct_intent,
                'timestamp': datetime.now().isoformat()
            })
            self.learned_patterns['correction_history'] = correction_history[-100:]
            
            self._save_learned_patterns()


    def _check_cache(self, message: str, context_key: str = "") -> Optional[Dict]:
        """Check if similar query was processed recently"""
        cache_key = f"nlp_cache:{hash(message.lower() + context_key)}"
        return cache.get(cache_key)
    
    def _cache_result(self, message: str, result: Dict, context_key: str = ""):
        """Cache processing result for 30 minutes"""
        cache_key = f"nlp_cache:{hash(message.lower() + context_key)}"
        cache.set(cache_key, result, timeout=1800)
    
    def handle_inappropriate_content(self, message: str, safety_issues: List[str]) -> Dict[str, str]:
        """Generate appropriate response for inappropriate content"""
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