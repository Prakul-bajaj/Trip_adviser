import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { chatAPI } from '../../services/api';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import ChatHistory from './ChatHistory';
import { Menu, X, MessageSquarePlus } from 'lucide-react';
import './Chat.css';

const ChatInterface = () => {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);
  const [conversations, setConversations] = useState([]);
  const [currentConversation, setCurrentConversation] = useState(null);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    } else {
      setMessages([]);
      setCurrentConversation(null);
    }
  }, [conversationId]);

  const loadConversations = async () => {
    try {
      const response = await chatAPI.getConversations();
      setConversations(response.data);
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      setLoading(true);
      const response = await chatAPI.getConversation(id);
      setMessages(response.data.messages || []);
      setCurrentConversation(response.data);
    } catch (error) {
      console.error('Error loading conversation:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (messageText) => {
    let convId = conversationId;

    // Create new conversation if none exists
    if (!convId) {
      try {
        const response = await chatAPI.createConversation();
        convId = response.data.id;
        navigate(`/chat/${convId}`);
        await loadConversations();
      } catch (error) {
        console.error('Error creating conversation:', error);
        return;
      }
    }

    // Add user message immediately
    const userMessage = {
      id: Date.now(),
      content: messageText,
      sender: 'user',
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      setLoading(true);
      const response = await chatAPI.sendMessage(convId, messageText);
      
      // Add bot response
      const botMessage = {
        id: Date.now() + 1,
        content: response.data.response,
        sender: 'bot',
        timestamp: new Date().toISOString(),
        suggestions: response.data.suggestions || [],
      };
      setMessages(prev => [...prev, botMessage]);
      
      // Reload conversations to update title
      await loadConversations();
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        content: 'Sorry, I encountered an error. Please try again.',
        sender: 'bot',
        timestamp: new Date().toISOString(),
        isError: true,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    navigate('/chat');
    setMessages([]);
    setCurrentConversation(null);
  };

  const handleSelectConversation = (id) => {
    navigate(`/chat/${id}`);
    if (window.innerWidth <= 768) {
      setSidebarOpen(false);
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await chatAPI.deleteConversation(id);
      await loadConversations();
      if (conversationId === id) {
        navigate('/chat');
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  return (
    <div className="chat-container">
      {sidebarOpen && (
        <div className="chat-sidebar">
          <div className="sidebar-header">
            <button 
              className="btn-new-chat"
              onClick={handleNewChat}
            >
              <MessageSquarePlus size={20} />
              New Chat
            </button>
            <button 
              className="btn-close-sidebar"
              onClick={() => setSidebarOpen(false)}
            >
              <X size={20} />
            </button>
          </div>
          <ChatHistory
            conversations={conversations}
            currentId={conversationId}
            onSelect={handleSelectConversation}
            onDelete={handleDeleteConversation}
          />
        </div>
      )}

      <div className="chat-main">
        <div className="chat-header">
          {!sidebarOpen && (
            <button 
              className="btn-menu"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu size={24} />
            </button>
          )}
          <h2>{currentConversation?.title || 'Trip Adviser Chat'}</h2>
        </div>

        <MessageList 
          messages={messages} 
          loading={loading}
        />

        <MessageInput 
          onSend={handleSendMessage}
          disabled={loading}
        />
      </div>
    </div>
  );
};

export default ChatInterface;