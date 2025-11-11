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
            logger.info("✅ spaCy loaded successfully")
        except OSError:
            logger.warning("⚠️ spaCy model not found. Run: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Initialize Gemini
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
            logger.info("✅ Gemini API configured")
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
        
        return {
            'intent_patterns': {},
            'entity_patterns': {},
            'phrase_mappings': {},
            'correction_history': []
        }
    
    def _save_learned_patterns(self):
        """Save learned patterns to cache"""
        cache.set('nlp_learned_patterns', json.dumps(self.learned_patterns), timeout=None)
    
    def process_message(self, message: str, user_id: str, session_context: Dict = None) -> Dict[str, Any]:
        """
        Main processing pipeline:
        1. Check cache for similar queries
        2. spaCy entity extraction (fast)
        3. Gemini intent + safety check (if needed)
        4. Learn from interaction
        """
        message_clean = message.strip()
        
        # Step 1: Check cache for exact/similar matches
        cached_result = self._check_cache(message_clean)
        if cached_result:
            logger.info(f"✅ Cache hit for: {message_clean[:50]}")
            return cached_result
        
        # Step 2: spaCy entity extraction
        entities = self._extract_entities_spacy(message_clean)
        
        # Step 3: Check learned patterns first
        learned_intent = self._check_learned_patterns(message_clean)
        
        # Step 4: Gemini for intent + safety
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
        
        # Extract activities using keywords
        activity_keywords = {
            'adventure': ['adventure', 'trekking', 'hiking', 'rafting', 'paragliding'],
            'beach': ['beach', 'sea', 'ocean', 'coastal'],
            'cultural': ['cultural', 'heritage', 'temple', 'monument', 'historical'],
            'wildlife': ['wildlife', 'safari', 'animals', 'jungle'],
            'spiritual': ['spiritual', 'pilgrimage', 'religious', 'temple'],
            'relaxation': ['relax', 'peaceful', 'calm', 'wellness', 'spa'],
            'food': ['food', 'culinary', 'cuisine', 'restaurant']
        }
        
        message_lower = message.lower()
        for activity, keywords in activity_keywords.items():
            if any(kw in message_lower for kw in keywords):
                entities['activities'].append(activity)
        
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
    
    def _fallback_entity_extraction(self, message: str) -> Dict[str, Any]:
        """Fallback entity extraction when spaCy not available"""
        entities = {
            'locations': [],
            'activities': [],
            'budget': None,
            'durations': [],
        }
        
        # Simple regex-based extraction
        budget_match = re.search(r'(\d+)k?\s*(budget|rupees|rs)?', message.lower())
        if budget_match:
            amount = int(budget_match.group(1))
            if amount < 1000:
                amount *= 1000
            entities['budget'] = {'amount': amount, 'max': amount}
        
        duration_match = re.search(r'(\d+)\s*days?', message.lower())
        if duration_match:
            entities['durations'].append(int(duration_match.group(1)))
        
        return entities
    
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
        """Build structured prompt for Gemini"""
        
        context_info = ""
        if context:
            context_info = f"""
Previous conversation context:
- Current topic: {context.get('current_topic', 'None')}
- Last intent: {context.get('last_intent', 'None')}
- Discussed destinations: {', '.join(context.get('mentioned_destinations', [])[:3])}
"""
        
        prompt = f"""You are an AI assistant for a travel planning chatbot. Analyze this user message and return a JSON response.

User message: "{message}"

Extracted entities: {json.dumps(entities)}

{context_info}

Your task:
1. Classify the INTENT (greeting, farewell, search, budget, duration, weather, recommendation, bookmark, safety, trip_planning, more_info, reference, general, inappropriate)
2. Assess CONTENT SAFETY (check for vulgar language, extreme religious views, harmful content)
3. Determine CONFIDENCE (0.0 to 1.0)
4. Provide CONTEXT UNDERSTANDING
5. Suggest RESPONSE TYPE (friendly, informative, cautious, firm_decline)

Return ONLY valid JSON in this exact format:
{{
  "intent": "search|budget|duration|weather|recommendation|greeting|farewell|inappropriate|general",
  "confidence": 0.95,
  "is_safe": true,
  "safety_issues": [],
  "context_understanding": "User is asking about beach destinations within budget",
  "suggested_response_type": "informative",
  "reasoning": "Brief explanation of classification"
}}

Content Safety Guidelines:
- Mark as "inappropriate" if: profanity, hate speech, sexual content, violence, illegal activities
- Safety issues can be: "vulgar", "religious_extreme", "harmful", "spam", "offensive"
- Set is_safe to false if ANY safety issue detected

Intent Classification:
- "search": Looking for destinations/places
- "budget": Asking about costs/prices/budget
- "duration": Specifying trip length
- "weather": Asking about climate/weather
- "recommendation": Wants personalized suggestions
- "reference": Referring to previous results ("the first one", "which of these")
- "greeting": Hi, hello, etc.
- "farewell": Bye, goodbye, etc.
- "inappropriate": Unsafe content
- "general": Help/unclear queries

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
        """Fallback when Gemini unavailable - use rule-based classification"""
        message_lower = message.lower()
        
        # Rule-based intent detection
        intent = 'general'
        confidence = 0.6
        
        if any(word in message_lower for word in ['hi', 'hello', 'hey', 'namaste']):
            intent = 'greeting'
            confidence = 0.9
        elif any(word in message_lower for word in ['bye', 'goodbye', 'later']):
            intent = 'farewell'
            confidence = 0.9
        elif any(word in message_lower for word in ['show', 'find', 'search', 'looking for']):
            intent = 'search'
            confidence = 0.8
        elif 'budget' in message_lower or entities.get('budget'):
            intent = 'budget'
            confidence = 0.8
        elif 'days' in message_lower or entities.get('durations'):
            intent = 'duration'
            confidence = 0.8
        elif any(word in message_lower for word in ['weather', 'temperature', 'climate']):
            intent = 'weather'
            confidence = 0.8
        elif any(word in message_lower for word in ['recommend', 'suggest']):
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
            'context_understanding': f"Detected as {intent} query",
            'suggested_response_type': 'informative' if is_safe else 'firm_decline'
        }
    
    def _check_learned_patterns(self, message: str) -> Optional[str]:
        """Check if message matches learned patterns"""
        message_lower = message.lower()
        
        # Check phrase mappings
        phrase_mappings = self.learned_patterns.get('phrase_mappings', {})
        for known_phrase, intent in phrase_mappings.items():
            if self._fuzzy_match(message_lower, known_phrase, threshold=0.85):
                logger.info(f"✅ Matched learned pattern: {known_phrase} -> {intent}")
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
            logger.info(f"📚 Learning: '{message_clean}' -> {correct_intent} (was {detected_intent})")
            
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