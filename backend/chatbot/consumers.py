import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat
    """
    
    async def connect(self):
        """
        Handle WebSocket connection
        """
        self.user = self.scope['user']
        
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
        
        # Send connection success message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to chatbot'
        }))
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection
        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
        
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send_error('An error occurred')
    
    async def handle_message(self, data):
        """
        Handle incoming chat message
        """
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return
        
        # Save user message
        user_message = await self.save_message(
            sender_type='user',
            content=message_text
        )
        
        # Process message and generate response
        bot_response = await self.process_message(message_text)
        
        # Save bot message
        bot_message = await self.save_message(
            sender_type='bot',
            content=bot_response['content'],
            detected_intent=bot_response.get('intent'),
            detected_entities=bot_response.get('entities', {})
        )
        
        # Send bot response
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': bot_response['content'],
            'timestamp': bot_message.timestamp.isoformat(),
            'intent': bot_response.get('intent'),
            'quick_replies': bot_response.get('quick_replies', []),
            'suggestions': bot_response.get('suggestions', [])
        }))
    
    async def handle_typing(self, data):
        """
        Handle typing indicator
        """
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'is_typing': is_typing
            }
        )
    
    @database_sync_to_async
    def save_message(self, sender_type, content, detected_intent=None, detected_entities=None):
        """
        Save message to database
        """
        from .models import Message, ChatSession
        
        session = ChatSession.objects.get(id=self.session_id)
        
        message = Message.objects.create(
            session=session,
            sender_type=sender_type,
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
    def process_message(self, message_text):
        """
        Process message and generate bot response
        """
        from .intent_classifier import IntentClassifier
        from .entity_extractor import ContextManager
        from .conversation_manager import ConversationManager
        from .models import ChatSession
        
        # Get session
        session = ChatSession.objects.get(id=self.session_id)
        
        # Classify intent
        classifier = IntentClassifier()
        intent_result = classifier.classify_intent(message_text)
        detected_intent = intent_result['intent']
        
        # Extract entities and update context
        context_manager = ContextManager(session)
        context_manager.update_context(message_text, detected_intent)
        
        # Generate response
        conv_manager = ConversationManager(session, self.user)
        response = conv_manager.generate_response(
            message_text,
            detected_intent,
            intent_result['confidence']
        )
        
        return response
    
    async def send_error(self, error_message):
        """
        Send error message to client
        """
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))
    
    async def typing_indicator(self, event):
        """
        Send typing indicator to client
        """
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': event['is_typing']
        }))