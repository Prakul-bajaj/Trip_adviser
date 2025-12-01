import React, { useState } from 'react';
import { MessageSquare, Trash2, MoreVertical } from 'lucide-react';
import './Chat.css';

const ChatHistory = ({ conversations, currentId, onSelect, onDelete }) => {
  const [menuOpen, setMenuOpen] = useState(null);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const groupConversationsByDate = () => {
    const groups = {
      today: [],
      yesterday: [],
      week: [],
      older: [],
    };

    conversations.forEach(conv => {
      const date = new Date(conv.updated_at || conv.created_at);
      const now = new Date();
      const diffDays = Math.ceil((now - date) / (1000 * 60 * 60 * 24));

      if (diffDays === 0) groups.today.push(conv);
      else if (diffDays === 1) groups.yesterday.push(conv);
      else if (diffDays < 7) groups.week.push(conv);
      else groups.older.push(conv);
    });

    return groups;
  };

  const groups = groupConversationsByDate();

  const toggleMenu = (e, id) => {
    e.stopPropagation();
    setMenuOpen(menuOpen === id ? null : id);
  };

  const handleDelete = (e, id) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      onDelete(id);
    }
    setMenuOpen(null);
  };

  const renderConversationGroup = (title, conversations) => {
    if (conversations.length === 0) return null;

    return (
      <div className="conversation-group">
        <div className="group-title">{title}</div>
        {conversations.map(conv => (
          <div 
            key={conv.id}
            className={`conversation-item ${currentId === conv.id ? 'active' : ''}`}
            onClick={() => onSelect(conv.id)}
          >
            <MessageSquare size={18} />
            <span className="conversation-title">
              {conv.title || 'New Conversation'}
            </span>
            <button 
              className="btn-menu-small"
              onClick={(e) => toggleMenu(e, conv.id)}
            >
              <MoreVertical size={16} />
            </button>
            {menuOpen === conv.id && (
              <div className="conversation-menu">
                <button onClick={(e) => handleDelete(e, conv.id)}>
                  <Trash2 size={16} />
                  Delete
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="chat-history">
      {conversations.length === 0 ? (
        <div className="empty-history">
          <p>No conversations yet</p>
          <p className="hint">Start a new chat to begin</p>
        </div>
      ) : (
        <>
          {renderConversationGroup('Today', groups.today)}
          {renderConversationGroup('Yesterday', groups.yesterday)}
          {renderConversationGroup('Previous 7 Days', groups.week)}
          {renderConversationGroup('Older', groups.older)}
        </>
      )}
    </div>
  );
};

export default ChatHistory;