from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat, name='chat'),
    path('sessions/', views.ChatSessionListCreateView.as_view(), name='chat-sessions'),
    path('sessions/<uuid:pk>/', views.ChatSessionDetailView.as_view(), name='chat-session-detail'),
    path('sessions/<uuid:session_id>/messages/', views.MessageListView.as_view(), name='messages'),
    path('feedback/', views.feedback, name='chat_feedback'),
]