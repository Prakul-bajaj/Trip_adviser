// ChatHistory.jsx - With Edit & Better UI

import React, { useState } from 'react';
import { MessageSquare, Trash2, Edit2, Check, X } from 'lucide-react';
import './Chat.css';

const ChatHistory = ({ conversations, currentId, onSelect, onDelete, onRename }) => {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const conversationList = Array.isArray(conversations) ? conversations : [];

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
  };

  const groupedConversations = conversationList.reduce((groups, conv) => {
    const date = formatDate(conv.started_at || conv.created_at);
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(conv);
    return groups;
  }, {});

  const handleStartEdit = (conv, e) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title || 'New Chat');
  };

  const handleSaveEdit = async (convId, e) => {
    e.stopPropagation();
    if (editTitle.trim() && onRename) {
      await onRename(convId, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  const handleCancelEdit = (e) => {
    e.stopPropagation();
    setEditingId(null);
    setEditTitle('');
  };

  if (conversationList.length === 0) {
    return (
      <div className="chat-history-empty">
        <MessageSquare size={48} />
        <p>No conversations yet</p>
        <small>Start a new chat to begin!</small>
      </div>
    );
  }

  return (
    <div className="chat-history">
      {Object.entries(groupedConversations).map(([date, convs]) => (
        <div key={date} className="history-group">
          <div className="history-group-date">{date}</div>
          {convs.map((conv) => (
            <div
              key={conv.id}
              className={`history-item ${currentId === conv.id ? 'active' : ''}`}
              onClick={() => editingId !== conv.id && onSelect(conv.id)}
            >
              {editingId === conv.id ? (
                <div className="history-item-edit">
                  <input
                    type="text"
                    className="history-edit-input"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveEdit(conv.id, e);
                      if (e.key === 'Escape') handleCancelEdit(e);
                    }}
                  />
                  <button
                    className="history-edit-btn save"
                    onClick={(e) => handleSaveEdit(conv.id, e)}
                    title="Save"
                  >
                    <Check size={14} />
                  </button>
                  <button
                    className="history-edit-btn cancel"
                    onClick={handleCancelEdit}
                    title="Cancel"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <>
                  <div className="history-item-content">
                    <MessageSquare size={16} />
                    <span className="history-item-title">
                      {conv.title || 'New Chat'}
                    </span>
                  </div>
                  <div className="history-item-actions">
                    <button
                      className="history-item-action"
                      onClick={(e) => handleStartEdit(conv, e)}
                      title="Edit name"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      className="history-item-action delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('Delete this conversation?')) {
                          onDelete(conv.id);
                        }
                      }}
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

export default ChatHistory;