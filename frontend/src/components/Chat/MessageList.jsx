// MessageList.jsx - With clickable suggestions

import React, { useEffect, useRef } from 'react';
import { User, Bot } from 'lucide-react';
import './Chat.css';

const MessageList = ({ messages, loading, onSuggestionClick }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  if (messages.length === 0 && !loading) {
    return (
      <div className="message-list">
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          textAlign: 'center',
          padding: '40px',
          color: '#999'
        }}>
          <Bot size={64} style={{ marginBottom: '20px', color: '#ddd' }} />
          <h3 style={{ margin: '0 0 10px', color: '#333' }}>Start a Conversation</h3>
          <p style={{ margin: 0, color: '#999' }}>
            Ask me about destinations, weather, or trip planning!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <div 
          key={message.id} 
          className={`message ${message.sender}`}
        >
          <div className="message-avatar">
            {message.sender === 'user' ? <User size={20} /> : <Bot size={20} />}
          </div>
          
          <div className="message-content">
            <div className={`message-bubble ${message.isError ? 'error' : ''}`}>
              {message.content}
            </div>
            
            {message.suggestions && message.suggestions.length > 0 && (
              <div className="message-suggestions">
                {message.suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    className="suggestion-chip"
                    onClick={() => onSuggestionClick && onSuggestionClick(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
            
            <div className="message-timestamp">
              {formatTime(message.timestamp)}
            </div>
          </div>
        </div>
      ))}
      
      {loading && (
        <div className="message bot">
          <div className="message-avatar">
            <Bot size={20} />
          </div>
          <div className="message-content">
            <div className="message-bubble">
              <div className="typing-indicator">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;