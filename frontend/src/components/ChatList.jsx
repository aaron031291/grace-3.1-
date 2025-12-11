import { useState } from "react";
import "./ChatList.css";

export default function ChatList({
  chats,
  selectedChatId,
  onSelectChat,
  onCreateChat,
  onDeleteChat,
  onUpdateTitle,
  loading,
}) {
  const [editingId, setEditingId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");

  const startEdit = (chat) => {
    setEditingId(chat.id);
    setEditingTitle(chat.title || "Untitled");
  };

  const saveEdit = (chatId) => {
    if (editingTitle.trim()) {
      onUpdateTitle(chatId, editingTitle);
    }
    setEditingId(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
  };

  return (
    <div className="chat-list-container">
      <div className="chat-list-header">
        <h2>Chats</h2>
        <button
          className="new-chat-btn"
          onClick={onCreateChat}
          title="New Chat"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
      </div>

      <div className="chat-list">
        {loading && <div className="chat-list-loading">Loading chats...</div>}
        {!loading && chats.length === 0 && (
          <div className="chat-list-empty">
            No chats yet. Create one to start!
          </div>
        )}
        {chats.map((chat) => (
          <div
            key={chat.id}
            className={`chat-item ${
              selectedChatId === chat.id ? "active" : ""
            }`}
          >
            <button
              className="chat-item-content"
              onClick={() => onSelectChat(chat.id)}
            >
              {editingId === chat.id ? (
                <input
                  type="text"
                  className="chat-title-input"
                  value={editingTitle}
                  onChange={(e) => setEditingTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") saveEdit(chat.id);
                    if (e.key === "Escape") cancelEdit();
                  }}
                  onClick={(e) => e.stopPropagation()}
                  autoFocus
                />
              ) : (
                <span className="chat-title">
                  {chat.title || "Untitled Chat"}
                </span>
              )}
            </button>
            {selectedChatId === chat.id && (
              <div className="chat-item-actions">
                {editingId === chat.id ? (
                  <>
                    <button
                      className="action-btn save"
                      onClick={() => saveEdit(chat.id)}
                      title="Save"
                    >
                      ✓
                    </button>
                    <button
                      className="action-btn cancel"
                      onClick={cancelEdit}
                      title="Cancel"
                    >
                      ✕
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className="action-btn edit"
                      onClick={() => startEdit(chat)}
                      title="Rename"
                    >
                      ✎
                    </button>
                    <button
                      className="action-btn delete"
                      onClick={() => {
                        if (confirm("Delete this chat?")) {
                          onDeleteChat(chat.id);
                        }
                      }}
                      title="Delete"
                    >
                      🗑
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
