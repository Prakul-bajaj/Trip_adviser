import re
import spacy
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import logging

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    Extract entities from user messages (dates, locations, budget, etc.)
    """
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("spaCy model not loaded. Run: python -m spacy download en_core_web_sm")
            self.nlp = None
    
    def extract_entities(self, text):
        """
        Extract all entities from text
        """
        entities = {
            'dates': self.extract_dates(text),
            'locations': self.extract_locations(text),
            'budget': self.extract_budget(text),
            'duration': self.extract_duration(text),
            'person_count': self.extract_person_count(text),
            'companion_type': self.extract_companion_type(text),
            'activities': self.extract_activities(text),
        }
        
        return {k: v for k, v in entities.items() if v}
    
    # Add this to EntityExtractor class in entity_extractor.py
    def extract(self, text):
        """Alias for extract_entities for compatibility"""
        return self.extract_entities(text)


    def extract_dates(self, text):
        """
        Extract dates from text
        """
        dates = []
        
        # Pattern 1: DD/MM/YYYY, DD-MM-YYYY
        date_pattern1 = r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b'
        matches = re.finditer(date_pattern1, text)
        for match in matches:
            try:
                date_str = match.group(0)
                parsed_date = date_parser.parse(date_str, dayfirst=True)
                dates.append(parsed_date.strftime('%Y-%m-%d'))
            except:
                pass
        
        # Pattern 2: Month names
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        for month_name, month_num in months.items():
            if month_name in text.lower():
                current_year = datetime.now().year
                dates.append(f"{current_year}-{month_num:02d}-01")
        
        # Pattern 3: Relative dates
        relative_patterns = {
            r'\b(next|this) week\b': 7,
            r'\b(next|this) month\b': 30,
            r'\btomorrow\b': 1,
            r'\bin (\d+) days?\b': None,
        }
        
        for pattern, days_offset in relative_patterns.items():
            match = re.search(pattern, text.lower())
            if match:
                if days_offset is None:
                    # Extract number from "in X days"
                    days_offset = int(re.search(r'(\d+)', match.group(0)).group(1))
                
                future_date = datetime.now() + timedelta(days=days_offset)
                dates.append(future_date.strftime('%Y-%m-%d'))
        
        return dates if dates else None
    
    def extract_locations(self, text):
        """
        Extract location/destination names
        """
        locations = []
        
        # Use spaCy NER if available
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ['GPE', 'LOC']:  # Geo-political entity or location
                    locations.append(ent.text)
        
        # Common Indian destinations (hardcoded for better accuracy)
        common_destinations = [
            'goa', 'manali', 'shimla', 'kerala', 'rajasthan', 'jaipur',
            'udaipur', 'ladakh', 'kashmir', 'delhi', 'mumbai', 'bangalore',
            'chennai', 'kolkata', 'agra', 'varanasi', 'rishikesh', 'darjeeling',
            'ooty', 'coorg', 'andaman', 'lakshadweep', 'hampi', 'mysore'
        ]
        
        text_lower = text.lower()
        for dest in common_destinations:
            if dest in text_lower:
                locations.append(dest.title())
        
        return list(set(locations)) if locations else None
    
    def extract_budget(self, text):
        """
        Extract budget information
        """
        budget_info = {}
        
        # Pattern: "budget of 50000", "50k budget", "around 30000"
        amount_patterns = [
            r'\b(\d+)k\b',  # 50k format
            r'\b(\d{4,})\b',  # Direct numbers
            r'\b(\d+)\s*(thousand|lakh|lakhs)\b'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text.lower())
            if match:
                amount = match.group(1)
                if 'k' in pattern:
                    amount = int(amount) * 1000
                elif 'lakh' in match.group(0):
                    amount = int(amount) * 100000
                elif 'thousand' in match.group(0):
                    amount = int(amount) * 1000
                else:
                    amount = int(amount)
                
                budget_info['amount'] = amount
                
                # Check for per person or total
                if 'per person' in text.lower():
                    budget_info['per_person'] = True
                else:
                    budget_info['per_person'] = False
                
                return budget_info
        
        # Budget range keywords
        budget_keywords = {
            'cheap': {'min': 0, 'max': 2000, 'category': 'Budget'},
            'budget': {'min': 0, 'max': 2000, 'category': 'Budget'},
            'affordable': {'min': 2000, 'max': 5000, 'category': 'Mid-Range'},
            'moderate': {'min': 2000, 'max': 5000, 'category': 'Mid-Range'},
            'expensive': {'min': 10000, 'max': 25000, 'category': 'Luxury'},
            'luxury': {'min': 10000, 'max': 50000, 'category': 'Luxury'},
        }
        
        text_lower = text.lower()
        for keyword, budget_range in budget_keywords.items():
            if keyword in text_lower:
                return budget_range
        
        return None
    
    def extract_duration(self, text):
        """
        Extract trip duration
        """
        # Pattern: "for 5 days", "3 day trip", "week long"
        duration_patterns = [
            (r'(\d+)\s*(day|days)', 'days'),
            (r'(\d+)\s*(night|nights)', 'nights'),
            (r'(\d+)\s*(week|weeks)', 'weeks'),
            (r'(weekend|long weekend)', 'weekend'),
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
                
                return {'value': value, 'unit': 'days'}
        
        return None
    
    def extract_person_count(self, text):
        """
        Extract number of people traveling
        """
        # Pattern: "4 people", "group of 6", "5 of us"
        count_patterns = [
            r'(\d+)\s*(people|persons|travelers)',
            r'group of (\d+)',
            r'(\d+) of us',
            r'(\d+)\s*adults?',
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, text.lower())
            if match:
                count = int(match.group(1))
                return count
        
        return None
    
    def extract_companion_type(self, text):
        """
        Extract companion type (family, friends, solo, etc.)
        """
        companion_patterns = {
            'solo': r'\b(solo|alone|myself|by myself)\b',
            'couple': r'\b(couple|partner|spouse|wife|husband|girlfriend|boyfriend)\b',
            'family': r'\b(family|parents|kids|children)\b',
            'friends': r'\b(friends|buddies|colleagues)\b',
            'group': r'\b(group|team)\b',
        }
        
        text_lower = text.lower()
        for companion_type, pattern in companion_patterns.items():
            if re.search(pattern, text_lower):
                return companion_type
        
        return None
    
    def extract_activities(self, text):
        """
        Extract activity/interest keywords
        """
        activity_keywords = {
            'adventure': ['adventure', 'trekking', 'hiking', 'rafting', 'paragliding', 'skiing'],
            'beach': ['beach', 'sea', 'ocean', 'swimming', 'surfing'],
            'cultural': ['culture', 'heritage', 'temple', 'museum', 'historical'],
            'food': ['food', 'cuisine', 'restaurant', 'culinary'],
            'shopping': ['shopping', 'market', 'bazaar'],
            'wildlife': ['wildlife', 'safari', 'animals', 'nature'],
            'photography': ['photography', 'photos', 'pictures'],
            'relaxation': ['relax', 'spa', 'wellness', 'peaceful', 'quiet'],
        }
        
        detected_activities = []
        text_lower = text.lower()
        
        for activity, keywords in activity_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_activities.append(activity)
        
        return detected_activities if detected_activities else None


class ContextManager:
    """
    Manage conversation context and extracted information
    """
    
    def __init__(self, session):
        self.session = session
        self.extractor = EntityExtractor()
    
    def update_context(self, message_text, detected_intent):
        """
        Update session context with new information
        """
        # Extract entities from message
        entities = self.extractor.extract_entities(message_text)
        
        # Get or create conversation state
        from chatbot.models import ConversationState
        state, created = ConversationState.objects.get_or_create(session=self.session)
        
        # Update extracted information
        if entities.get('dates'):
            dates = entities['dates']
            if len(dates) >= 2:
                state.travel_dates = {
                    'start_date': dates[0],
                    'end_date': dates[1]
                }
            elif len(dates) == 1:
                state.travel_dates = {'start_date': dates[0]}
        
        if entities.get('budget'):
            state.budget = entities['budget']
        
        if entities.get('companion_type') or entities.get('person_count'):
            state.companions = {
                'type': entities.get('companion_type'),
                'count': entities.get('person_count')
            }
        
        if entities.get('duration'):
            if not state.travel_dates.get('end_date') and state.travel_dates.get('start_date'):
                # Calculate end date from duration
                from datetime import datetime, timedelta
                start_date = datetime.strptime(state.travel_dates['start_date'], '%Y-%m-%d')
                duration_days = entities['duration']['value']
                end_date = start_date + timedelta(days=duration_days)
                state.travel_dates['end_date'] = end_date.strftime('%Y-%m-%d')
        
        if entities.get('activities'):
            state.interests = list(set(state.interests + entities['activities']))
        
        if entities.get('locations'):
    # Use state.extracted_info instead of self.session.extracted_info
            extracted_info = state.extracted_info if isinstance(state.extracted_info, dict) else {}
            if 'preferred_destinations' not in extracted_info:
                extracted_info['preferred_destinations'] = []
            extracted_info['preferred_destinations'].extend(entities['locations'])
            state.extracted_info = extracted_info
        
        # Update current flow based on intent
        flow_mapping = {
            'greeting': 'onboarding',
            'destination_query': 'searching',
            'itinerary_request': 'planning',
            'booking_help': 'booking',
            'feedback_submit': 'feedback',
        }
        
        if detected_intent in flow_mapping:
            state.current_flow = flow_mapping[detected_intent]
        
        state.save()
        
        return state
    
    def get_missing_information(self):
        """
        Determine what information is still needed
        """
        from chatbot.models import ConversationState
        try:
            state = ConversationState.objects.get(session=self.session)
        except ConversationState.DoesNotExist:
            return ['travel_dates', 'budget', 'companions', 'interests']
        
        missing = []
        
        if not state.travel_dates or not state.travel_dates.get('start_date'):
            missing.append('travel_dates')
        
        if not state.budget:
            missing.append('budget')
        
        if not state.companions:
            missing.append('companions')
        
        if not state.interests:
            missing.append('interests')
        
        return missing
    
    def is_information_complete(self):
        """
        Check if we have all required information
        """
        missing = self.get_missing_information()
        return len(missing) == 0