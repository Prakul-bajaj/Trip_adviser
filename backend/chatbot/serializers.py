from rest_framework import serializers
from .models import ChatSession, Message, ConversationState


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['timestamp']


class ConversationStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationState
        exclude = ['id', 'session']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages_count = serializers.IntegerField(source='total_messages', read_only=True)
    latest_messages = serializers.SerializerMethodField()
    state = ConversationStateSerializer(read_only=True)
    
    class Meta:
        model = ChatSession
        fields = '__all__'
        read_only_fields = ['user', 'started_at', 'last_activity_at', 'total_messages']
    
    def get_latest_messages(self, obj):
        messages = obj.messages.all()[:10]
        return MessageSerializer(messages, many=True).data