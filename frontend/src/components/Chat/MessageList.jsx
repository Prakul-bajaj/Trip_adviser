import React, { useEffect, useRef } from 'react';
import { Bot, User, Loader } from 'lucide-react';
import './Chat.css';

const MessageList = ({ messages, loading }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="messages-container">
      {messages.length === 0 && !loading && (
        <div className="empty-state">
          <Bot size={64} className="empty-icon" />
          <h3>Welcome to Trip Adviser!</h3>
          <p>Ask me anything about travel destinations, itineraries, or trip planning.</p>
          <div className="suggestion-chips">
            <div className="chip">Suggest destinations for summer vacation</div>
            <div className="chip">Plan a 5-day trip to Paris</div>
            <div className="chip">Best time to visit Japan</div>
          </div>
        </div>
      )}

      <div className="messages-list">
        {messages.map((message) => (
          <div 
            key={message.id} 
            className={`message ${message.sender}`}
          >
            <div className="message-avatar">
              {message.sender === 'user' ? (
                <User size={20} />
              ) : (
                <Bot size={20} />
              )}
            </div>
            <div className="message-content">
              <div className="message-text">
                {message.content}
              </div>
              {message.suggestions && message.suggestions.length > 0 && (
                <div className="message-suggestions">
                  {message.suggestions.map((suggestion, idx) => (
                    <div key={idx} className="suggestion-chip">
                      {suggestion}
                    </div>
                  ))}
                </div>
              )}
              <div className="message-time">
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
              <div className="typing-indicator">
                <Loader className="spinner" size={20} />
                <span>Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default MessageList;