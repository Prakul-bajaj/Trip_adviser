# chatbot/consumers.py - FIXED VERSION

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat with context awareness
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']
        self.room_group_name = None  # Initialize here to prevent AttributeError
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        self.room_group_name = f'chat_{self.user.id}_{self.session_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Load conversation history
        history = await self.load_conversation_history()
        
        # Send connection success with history
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to chatbot',
            'session_id': str(self.session_id),
            'conversation_history': history
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Only try to leave group if we successfully joined
        if hasattr(self, 'room_group_name') and self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'feedback':
                await self.handle_feedback(data)
        
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}", exc_info=True)
            await self.send_error('An error occurred processing your message')
    
    async def handle_message(self, data):
        """Handle incoming chat message with NLP processing"""
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return
        
        # Send typing indicator
        await self.send(text_data=json.dumps({
            'type': 'bot_typing',
            'is_typing': True
        }))
        
        # Save user message
        user_message = await self.save_message(
            sender='user',
            content=message_text
        )
        
        # Process message with NLP engine
        bot_response = await self.process_message_with_nlp(message_text)
        
        # Save bot message
        bot_message = await self.save_message(
            sender='bot',
            content=bot_response['message'],
            detected_intent=bot_response.get('detected_intent'),
            detected_entities=bot_response.get('entities', {})
        )
        
        # Stop typing indicator
        await self.send(text_data=json.dumps({
            'type': 'bot_typing',
            'is_typing': False
        }))
        
        # Send bot response
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': str(bot_message.id),
            'message': bot_response['message'],
            'timestamp': bot_message.timestamp.isoformat(),
            'intent': bot_response.get('detected_intent'),
            'confidence': bot_response.get('nlp_confidence'),
            'suggestions': bot_response.get('suggestions', []),
            'destinations': bot_response.get('destinations', []),
            'context': bot_response.get('context')
        }))
    
    async def handle_typing(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'is_typing': is_typing,
                'user': self.user.email
            }
        )
    
    async def handle_feedback(self, data):
        """Handle user feedback on bot responses"""
        message_id = data.get('message_id')
        feedback_type = data.get('feedback')  # 'positive', 'negative', 'correction'
        correct_intent = data.get('correct_intent')
        
        result = await self.save_feedback(message_id, feedback_type, correct_intent)
        
        await self.send(text_data=json.dumps({
            'type': 'feedback_received',
            'message': result['message'],
            'learned': result.get('learned', False)
        }))
    
    @database_sync_to_async
    def load_conversation_history(self):
        """Load recent conversation history"""
        from .models import Message, ChatSession
        
        try:
            session = ChatSession.objects.get(id=self.session_id, user=self.user)
            messages = Message.objects.filter(session=session).order_by('timestamp')[:50]
            
            return [
                {
                    'id': str(msg.id),
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'intent': msg.detected_intent
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []
    
    @database_sync_to_async
    def save_message(self, sender, content, detected_intent=None, detected_entities=None):
        """Save message to database"""
        from .models import Message, ChatSession
        
        session = ChatSession.objects.get(id=self.session_id)
        
        message = Message.objects.create(
            session=session,
            sender=sender,
            content=content,
            detected_intent=detected_intent or '',
            detected_entities=detected_entities or {}
        )
        
        # Update session
        session.total_messages += 1
        session.last_activity_at = timezone.now()
        session.save()
        
        return message
    
    @database_sync_to_async
    def process_message_with_nlp(self, message_text):
        """
        Process message using the enhanced NLP engine
        """
        from .models import ChatSession
        from .nlp_engine import get_nlp_engine
        from .context_manager import ConversationContextManager
        
        # Get session
        session = ChatSession.objects.get(id=self.session_id)
        
        # Get NLP engine
        nlp_engine = get_nlp_engine()
        
        # Get conversation context
        context_mgr = ConversationContextManager(session)
        context_summary = context_mgr.get_context_summary()
        
        # Process with NLP
        nlp_result = nlp_engine.process_message(
            message=message_text,
            user_id=str(self.user.id),
            session_context=context_summary
        )
        
        logger.info(f"WebSocket NLP: Intent={nlp_result['intent']}, Confidence={nlp_result['confidence']:.2f}")
        
        # Handle unsafe content
        if not nlp_result['is_safe']:
            safety_response = nlp_engine.handle_inappropriate_content(
                message_text,
                nlp_result['safety_issues']
            )
            
            return {
                'message': safety_response['message'],
                'detected_intent': 'inappropriate',
                'is_safe': False,
                'suggestions': [
                    "Show me destinations",
                    "Recommend places for me",
                    "Plan a trip"
                ]
            }
        
        # Route to appropriate handler
        from . import views
        
        detected_intent = nlp_result['intent']
        entities = nlp_result['entities']
        
        # Create a mock request object
        mock_request = type('Request', (), {
            'user': self.user,
            'data': {},
            'query_params': {}
        })()
        
        # Route based on intent
        if detected_intent == 'reference':
            response = views.handle_reference_query(mock_request, session, message_text, entities)
        elif detected_intent == 'greeting':
            response = views.handle_greeting(mock_request, session)
        elif detected_intent == 'farewell':
            response = views.handle_farewell(mock_request, session)
        elif detected_intent == 'attractions':
            response = views.handle_attractions_query(mock_request, session, message_text, entities)
        elif detected_intent == 'restaurants':
            response = views.handle_restaurants_query(mock_request, session, message_text, entities)
        elif detected_intent == 'accommodations':
            response = views.handle_accommodations_query(mock_request, session, message_text, entities)
        elif detected_intent == 'weather':
            response = views.handle_weather_query(mock_request, session, message_text, entities)
        elif detected_intent == 'recommendation':
            response = views.handle_personalized_recommendations(mock_request, session, message_text, entities)
        elif detected_intent == 'search':
            response = views.handle_destination_search_v2(mock_request, session, message_text, entities)
        elif detected_intent == 'budget':
            response = views.handle_budget_query_v2(mock_request, session, message_text, entities)
        elif detected_intent == 'more_info':
            response = views.handle_more_info(mock_request, session, message_text)
        elif detected_intent == 'bookmark':
            response = views.handle_bookmark(mock_request, session, message_text)
        elif detected_intent == 'safety':
            response = views.handle_safety_check(mock_request, session, message_text, entities)
        elif detected_intent == 'trip_planning':
            response = views.handle_itinerary_creation(mock_request, session, message_text, entities)
        else:
            response = views.handle_general_query(mock_request, session, message_text)
        
        # Add NLP metadata
        response['detected_intent'] = detected_intent
        response['nlp_confidence'] = nlp_result['confidence']
        response['nlp_source'] = nlp_result['source']
        response['entities'] = entities
        
        # Learn from interaction
        nlp_engine.learn_from_interaction(
            message=message_text,
            detected_intent=detected_intent,
            user_feedback='positive'
        )
        
        return response
    
    @database_sync_to_async
    def save_feedback(self, message_id, feedback_type, correct_intent):
        """Save user feedback and learn from it"""
        from .models import Message
        from .nlp_engine import get_nlp_engine
        
        try:
            message = Message.objects.get(id=message_id, session__user=self.user)
            
            # Get previous user message
            user_message = Message.objects.filter(
                session=message.session,
                sender='user',
                timestamp__lt=message.timestamp
            ).order_by('-timestamp').first()
            
            if not user_message:
                return {'message': 'Could not find original message', 'learned': False}
            
            # Learn from feedback
            nlp_engine = get_nlp_engine()
            nlp_engine.learn_from_interaction(
                message=user_message.content,
                detected_intent=message.detected_intent or 'general',
                user_feedback=feedback_type,
                correct_intent=correct_intent
            )
            
            logger.info(f"Learning from feedback: {user_message.content[:50]} -> {correct_intent or message.detected_intent}")
            
            return {
                'message': 'Thank you for your feedback! I\'m learning and improving. 🎓',
                'learned': True
            }
        
        except Exception as e:
            logger.error(f"Feedback error: {e}")
            return {'message': 'Error processing feedback', 'learned': False}
    
    async def send_error(self, error_message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to client"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': event['is_typing'],
            'user': event.get('user')
        }))