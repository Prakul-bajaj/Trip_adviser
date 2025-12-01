import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import pickle
import os
from utils.constants import INTENT_TYPES
import logging

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Classify user intents from text messages
    Uses rule-based + ML hybrid approach
    """
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.intent_patterns = self._build_intent_patterns()
        self.load_model()
    
    def _build_intent_patterns(self):
        """
        Define regex patterns for common intents
        """
        return {
            # NEW: Reference intent - MUST BE CHECKED FIRST
            'reference': [
                r'\b(the )?(first|second|third|last|top)\s+(one|place|destination|option)\b',
                r'\b(tell me|more about|info about|details about|show me)\s+(the )?(first|second|third|last|it|that|this)\b',
                r'\b(it|that|this|these|those)\b(?!.*\b(place|destination|is|are|will|should)\b)',
                r'\b(which of (these|those|them))\b',
                r'\b(any of (these|those|them))\b',
            ],
            'greeting': [
                r'^\s*(hi|hello|hey|greetings|good morning|good evening)\b',  # Must be at start
                r'\bhow are you\b',
                r'\bwhat\'?s up\b'
            ],
            'destination_query': [
                r'\b(where|which place|destination|visit|go to|travel to)\b',
                r'\b(suggest|recommend|show me|tell me about)\s+(place|destination|location)\b',
                r'\bwhat are (the )?(best|top|good)\s+(places|destinations)\b'
            ],
            'budget_query': [
                r'\b(how much|cost|price|budget|expensive|cheap|affordable)\b',
                r'\b(spend|spending)\b',
                r'\bmoney\b',
                r'\bunder\s+(\d+)k?\b',  # "under 30k"
                r'\bwithin\s+(\d+)k?\b'  # "within budget"
            ],
            'duration_query': [
                r'\b(\d+)\s*days?\b',
                r'\bfor\s+(\d+)\s+days?\b',
                r'\b(weekend|week)\b'
            ],
            'weather_query': [
                r'\b(weather|temperature|climate|rain|snow|sunny|cold|hot)\b',
                r'\bhow\'?s the weather\b',
                r'\bwill it rain\b'
            ],
            'itinerary_request': [
                r'\b(itinerary|plan|schedule|route)\b',
                r'\b(day by day|daily plan)\b',
                r'\bwhat (should|can) (i|we) do\b'
            ],
            'travel_dates': [
                r'\b(when|date|time|going|visit|traveling)\b',
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
                r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b'
            ],
            'companion_info': [
                r'\b(with|going with|traveling with)\b',
                r'\b(family|friends|solo|alone|couple|group)\b',
                r'\b(kids|children|elderly|parents)\b'
            ],
            'booking_help': [
                r'\b(book|booking|reserve|reservation)\b',
                r'\b(hotel|flight|train|ticket)\b'
            ],
            'more_info': [
                r'\b(tell me more|more info|details|elaborate)\b',
                r'\bwhat about\b',
                r'\bhow about\b'
            ],
            'feedback_submit': [
                r'\b(feedback|review|rating|complain|complaint|suggest|suggestion)\b',
                r'\b(good|bad|excellent|poor|love|hate)\b\s+(experience|service|recommendation)'
            ],
            'emergency_help': [
                r'\b(emergency|urgent|help|problem|issue|stuck)\b',
                r'\b(lost|theft|accident|medical)\b'
            ],
            'goodbye': [
                r'\b(bye|goodbye|see you|thanks|thank you|exit|quit)\b'
            ]
        }
    
    def classify_intent(self, text, has_context=False):
        """
        Classify intent using hybrid approach
        has_context: True if there are previous results in context
        """
        text_lower = text.lower().strip()
        
        # CRITICAL: Check reference intent FIRST if context exists
        if has_context:
            reference_patterns = self.intent_patterns.get('reference', [])
            for pattern in reference_patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return {
                        'intent': 'reference',
                        'confidence': 0.95,
                        'method': 'rule_based_priority'
                    }
        
        # Then try other rule-based classification
        rule_based_intent = self._rule_based_classification(text_lower)
        if rule_based_intent:
            return {
                'intent': rule_based_intent,
                'confidence': 0.9,
                'method': 'rule_based'
            }
        
        # Fall back to ML model if trained
        if self.model and self.vectorizer:
            ml_intent, confidence = self._ml_classification(text_lower)
            return {
                'intent': ml_intent,
                'confidence': confidence,
                'method': 'ml_model'
            }
        
        # Default to general_info if uncertain
        return {
            'intent': 'general_info',
            'confidence': 0.5,
            'method': 'default'
        }
    
    def _rule_based_classification(self, text):
        """
        Use regex patterns to classify intent
        """
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return intent
        return None
    
    def _ml_classification(self, text):
        """
        Use trained ML model to classify intent
        """
        try:
            features = self.vectorizer.transform([text])
            prediction = self.model.predict(features)[0]
            probabilities = self.model.predict_proba(features)[0]
            confidence = max(probabilities)
            
            return prediction, confidence
        except Exception as e:
            logger.error(f"ML classification error: {str(e)}")
            return 'general_info', 0.5
    
    def load_model(self):
        """
        Load pre-trained model if exists
        """
        model_path = 'ml_models/saved_models/intent_classifier.pkl'
        vectorizer_path = 'ml_models/saved_models/intent_vectorizer.pkl'
        
        if os.path.exists(model_path) and os.path.exists(vectorizer_path):
            try:
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(vectorizer_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                logger.info("Intent classifier model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading intent model: {str(e)}")
    
    def train_model(self, training_data):
        """
        Train the intent classification model
        training_data: list of tuples [(text, intent), ...]
        """
        if not training_data:
            logger.warning("No training data provided")
            return
        
        texts, intents = zip(*training_data)
        
        # Create TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words='english'
        )
        
        # Transform texts to features
        X = self.vectorizer.fit_transform(texts)
        
        # Train Naive Bayes classifier
        self.model = MultinomialNB()
        self.model.fit(X, intents)
        
        # Save model
        self.save_model()
        
        logger.info(f"Intent classifier trained on {len(training_data)} samples")
    
    def save_model(self):
        """
        Save trained model to disk
        """
        os.makedirs('ml_models/saved_models', exist_ok=True)
        
        model_path = 'ml_models/saved_models/intent_classifier.pkl'
        vectorizer_path = 'ml_models/saved_models/intent_vectorizer.pkl'
        
        try:
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
            with open(vectorizer_path, 'wb') as f:
                pickle.dump(self.vectorizer, f)
            logger.info("Intent classifier model saved successfully")
        except Exception as e:
            logger.error(f"Error saving intent model: {str(e)}")


# Sample training data for initial model
SAMPLE_TRAINING_DATA = [
    # Greetings
    ("hi there", "greeting"),
    ("hello", "greeting"),
    ("good morning", "greeting"),
    ("hey how are you", "greeting"),
    
    # Reference queries - NEW
    ("tell me about the first one", "reference"),
    ("the second one", "reference"),
    ("more about that place", "reference"),
    ("details about it", "reference"),
    ("what about the last one", "reference"),
    
    # Destination queries
    ("where should I go", "destination_query"),
    ("suggest a place to visit", "destination_query"),
    ("tell me about goa", "destination_query"),
    ("best places in india", "destination_query"),
    ("want to visit mountains", "destination_query"),
    
    # Budget queries
    ("how much will it cost", "budget_query"),
    ("what's my budget", "budget_query"),
    ("is it expensive", "budget_query"),
    ("cheap destinations", "budget_query"),
    ("under 30k budget", "budget_query"),
    
    # Duration queries
    ("for 5 days", "duration_query"),
    ("a week long trip", "duration_query"),
    
    # Weather queries
    ("what's the weather like", "weather_query"),
    ("will it rain", "weather_query"),
    ("is it cold there", "weather_query"),
    
    # Itinerary
    ("create an itinerary", "itinerary_request"),
    ("plan my trip", "itinerary_request"),
    ("what should I do there", "itinerary_request"),
    
    # Travel dates
    ("I'm going in december", "travel_dates"),
    ("planning for next month", "travel_dates"),
    ("when is the best time to visit", "travel_dates"),
    
    # Companion info
    ("going with family", "companion_info"),
    ("solo trip", "companion_info"),
    ("traveling with friends", "companion_info"),
    
    # Goodbye
    ("bye", "goodbye"),
    ("thank you", "goodbye"),
    ("that's all", "goodbye"),
]