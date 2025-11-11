# chatbot/entity_extractor.py - SIMPLIFIED VERSION
# This is now mostly a fallback - NLP engine handles primary extraction

import re
import logging
from datetime import datetime, timedelta
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    SIMPLIFIED: Basic entity extraction as fallback
    Primary extraction now handled by HybridNLPEngine
    """
    
    def __init__(self):
        logger.info("EntityExtractor initialized (fallback mode)")
    
    def extract_entities(self, text):
        """
        Basic entity extraction - used as fallback when NLP engine unavailable
        """
        entities = {}
        
        # Extract budget
        budget = self.extract_budget(text)
        if budget:
            entities['budget'] = budget
        
        # Extract duration
        duration = self.extract_duration(text)
        if duration:
            entities['duration'] = duration
        
        # Extract person count
        person_count = self.extract_person_count(text)
        if person_count:
            entities['person_count'] = person_count
        
        # Extract activities (basic)
        activities = self.extract_activities(text)
        if activities:
            entities['activities'] = activities
        
        # Extract locations (basic)
        locations = self.extract_locations(text)
        if locations:
            entities['locations'] = locations
        
        return {k: v for k, v in entities.items() if v}
    
    def extract(self, text):
        """Alias for compatibility"""
        return self.extract_entities(text)
    
    def extract_budget(self, text):
        """Extract budget information"""
        budget_info = {}
        
        amount_patterns = [
            (r'(\d+)k\b', lambda m: int(m.group(1)) * 1000),
            (r'(\d{4,})', lambda m: int(m.group(1))),
            (r'(\d+)\s*(lakh|lakhs)', lambda m: int(m.group(1)) * 100000),
        ]
        
        for pattern, converter in amount_patterns:
            match = re.search(pattern, text.lower())
            if match:
                amount = converter(match)
                budget_info['amount'] = amount
                budget_info['per_person'] = 'per person' in text.lower()
                return budget_info
        
        # Budget keywords
        budget_keywords = {
            'cheap': {'min': 0, 'max': 20000, 'category': 'Budget'},
            'budget': {'min': 0, 'max': 25000, 'category': 'Budget'},
            'affordable': {'min': 20000, 'max': 50000, 'category': 'Mid-Range'},
            'expensive': {'min': 50000, 'max': 100000, 'category': 'Premium'},
            'luxury': {'min': 100000, 'max': 250000, 'category': 'Luxury'},
        }
        
        text_lower = text.lower()
        for keyword, budget_range in budget_keywords.items():
            if keyword in text_lower:
                return budget_range
        
        return None
    
    def extract_duration(self, text):
        """Extract trip duration"""
        duration_patterns = [
            (r'(\d+)\s*days?', 'days'),
            (r'(\d+)\s*nights?', 'nights'),
            (r'(\d+)\s*weeks?', 'weeks'),
            (r'weekend|long weekend', 'weekend'),
        ]
        
        for pattern, unit in duration_patterns:
            match = re.search(pattern, text.lower())
            if match:
                if unit == 'weekend':
                    return {'value': 2, 'unit': 'days'}
                
                value = int(match.group(1))
                if unit == 'weeks':
                    value = value * 7
                    unit = 'days'
                elif unit == 'nights':
                    value = value + 1
                    unit = 'days'
                
                return {'value': value, 'unit': 'days', 'days': value}
        
        return None
    
    def extract_person_count(self, text):
        """Extract number of people"""
        count_patterns = [
            r'(\d+)\s*(people|persons|travelers|pax)',
            r'group of (\d+)',
            r'(\d+) of us',
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1))
        
        # Special cases
        if 'solo' in text.lower() or 'alone' in text.lower():
            return 1
        elif 'couple' in text.lower():
            return 2
        elif 'family' in text.lower():
            return 4
        
        return None
    
    def extract_activities(self, text):
        """Extract activity keywords"""
        activity_keywords = {
            'adventure': ['adventure', 'trekking', 'hiking', 'rafting'],
            'beach': ['beach', 'sea', 'ocean', 'coastal'],
            'cultural': ['cultural', 'heritage', 'temple', 'historical'],
            'wildlife': ['wildlife', 'safari', 'animals', 'jungle'],
            'spiritual': ['spiritual', 'pilgrimage', 'religious'],
            'relaxation': ['relax', 'peaceful', 'spa', 'wellness'],
            'food': ['food', 'cuisine', 'culinary'],
        }
        
        detected = []
        text_lower = text.lower()
        
        for activity, keywords in activity_keywords.items():
            if any(kw in text_lower for kw in keywords):
                detected.append(activity)
        
        return detected if detected else None
    
    def extract_locations(self, text):
        """Extract location names (basic)"""
        common_destinations = [
            'goa', 'manali', 'shimla', 'kerala', 'jaipur', 'udaipur',
            'ladakh', 'kashmir', 'delhi', 'mumbai', 'rishikesh',
            'varanasi', 'darjeeling', 'ooty', 'coorg', 'hampi'
        ]
        
        found = []
        text_lower = text.lower()
        
        for dest in common_destinations:
            if dest in text_lower:
                found.append(dest.title())
        
        return found if found else None
    
    def extract_weather_preference(self, text):
        """Extract weather preferences"""
        weather_patterns = {
            'cold': r'\b(cold|cool|chilly)\b',
            'hot': r'\b(hot|warm|sunny)\b',
            'pleasant': r'\b(pleasant|moderate|comfortable)\b',
        }
        
        text_lower = text.lower()
        for preference, pattern in weather_patterns.items():
            if re.search(pattern, text_lower):
                return preference
        
        return None
    
    def extract_time_frame(self, text):
        """Extract time frames"""
        time_patterns = {
            r'next\s+(\d+)\s+days?': lambda m: {'start': 0, 'end': int(m.group(1)), 'unit': 'days'},
            r'this\s+weekend': lambda m: {'start': 0, 'end': 3, 'unit': 'days', 'type': 'weekend'},
            r'next\s+week': lambda m: {'start': 7, 'end': 14, 'unit': 'days'},
        }
        
        text_lower = text.lower()
        for pattern, extractor in time_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                return extractor(match)
        
        return None
    
    def extract_climate_preference(self, text):
        """Extract climate preferences"""
        climate_keywords = {
            'tropical': ['tropical', 'humid', 'coastal'],
            'alpine': ['alpine', 'mountain', 'hills', 'snow'],
            'arid': ['desert', 'dry'],
            'temperate': ['temperate', 'moderate'],
        }
        
        detected = []
        text_lower = text.lower()
        
        for climate, keywords in climate_keywords.items():
            if any(kw in text_lower for kw in keywords):
                detected.append(climate)
        
        return detected if detected else None


# Keep for backward compatibility
class ContextManager:
    """
    DEPRECATED: Use ConversationContextManager instead
    Kept for backward compatibility only
    """
    
    def __init__(self, session):
        self.session = session
        self.extractor = EntityExtractor()
        logger.warning("ContextManager is deprecated. Use ConversationContextManager instead.")
    
    def update_context(self, message_text, detected_intent):
        """Deprecated - context updates now handled by ConversationContextManager"""
        logger.warning("update_context is deprecated")
        pass
    
    def get_missing_information(self):
        """Deprecated"""
        logger.warning("get_missing_information is deprecated")
        return []
    
    def is_information_complete(self):
        """Deprecated"""
        logger.warning("is_information_complete is deprecated")
        return False