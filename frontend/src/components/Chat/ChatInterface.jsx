// ChatInterface.jsx - Fixed: Load messages + Rename + Toggle sidebar

import React, { useState, useEffect } from 'react';
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
      const data = response.data;
      setConversations(Array.isArray(data) ? data : data.results || []);
    } catch (error) {
      console.error('Error loading conversations:', error);
      setConversations([]);
    }
  };

  const loadConversation = async (id) => {
    try {
      setLoading(true);
      
      // Load conversation details
      const response = await chatAPI.getConversation(id);
      const data = response.data;
      
      console.log('📥 Loaded conversation:', data);
      
      // Load messages for this conversation
      try {
        const messagesResponse = await chatAPI.getMessages(id);
        const messagesData = messagesResponse.data;
        
        console.log('📨 Loaded messages:', messagesData);
        
        // Handle different response structures
        const messagesList = Array.isArray(messagesData) 
          ? messagesData 
          : (messagesData.results || messagesData.messages || []);
        
        setMessages(messagesList);
      } catch (msgError) {
        console.error('Error loading messages:', msgError);
        // Fallback to messages in conversation data
        setMessages(Array.isArray(data.messages) ? data.messages : []);
      }
      
      setCurrentConversation(data);
    } catch (error) {
      console.error('Error loading conversation:', error);
      setMessages([]);
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
      const botResponse = response.data;
      
      const botMessage = {
        id: Date.now() + 1,
        content: botResponse.message || botResponse.response || 'No response',
        sender: 'bot',
        timestamp: new Date().toISOString(),
        suggestions: botResponse.suggestions || [],
        destinations: botResponse.destinations || [],
      };
      
      setMessages(prev => [...prev, botMessage]);
      await loadConversations();
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage = {
        id: Date.now() + 1,
        content: error.response?.data?.message || 'Sorry, I encountered an error. Please try again.',
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

  const handleRenameConversation = async (id, newTitle) => {
    try {
      await chatAPI.updateConversation(id, { title: newTitle });
      await loadConversations();
      if (currentConversation && currentConversation.id === id) {
        setCurrentConversation({ ...currentConversation, title: newTitle });
      }
    } catch (error) {
      console.error('Error renaming conversation:', error);
    }
  };

  // ✅ FIX: Handle suggestion clicks
  const handleSuggestionClick = (suggestion) => {
    handleSendMessage(suggestion);
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
            {window.innerWidth <= 768 && (
              <button 
                className="btn-close-sidebar"
                onClick={() => setSidebarOpen(false)}
              >
                <X size={20} />
              </button>
            )}
          </div>
          <ChatHistory
            conversations={conversations}
            currentId={conversationId}
            onSelect={handleSelectConversation}
            onDelete={handleDeleteConversation}
            onRename={handleRenameConversation}
          />
        </div>
      )}

      <div className="chat-main">
        <div className="chat-header">
          <button 
            className="btn-menu"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
          >
            {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
          <h2>{currentConversation?.title || 'Trip Adviser Chat'}</h2>
        </div>

        <MessageList 
          messages={messages} 
          loading={loading}
          onSuggestionClick={handleSuggestionClick}
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