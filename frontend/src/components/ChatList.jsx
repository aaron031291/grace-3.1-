import { useState, useEffect } from "react";
import "./ChatList.css";

const API_BASE = "http://localhost:8000";

export default function ChatList({
  chats,
  selectedChatId,
  selectedFolder,
  onSelectChat,
  onSelectFolder,
  onCreateChat,
  onDeleteChat,
  onUpdateTitle,
  loading,
}) {
  const [editingId, setEditingId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [folders, setFolders] = useState([]);
  const [generalChatCount, setGeneralChatCount] = useState(0);
  const [loadingFolders, setLoadingFolders] = useState(true);
  const [showNewFolderInput, setShowNewFolderInput] = useState(false);
  const [newFolderPath, setNewFolderPath] = useState("");
  const [chatMode, setChatMode] = useState("general"); // "general" or "folders"
  const [expandedFolder, setExpandedFolder] = useState(null);
  const [showModeDropdown, setShowModeDropdown] = useState(false);

  // Fetch folders on mount
  useEffect(() => {
    fetchFolders();
  }, []);

  // Update mode based on selectedFolder
  useEffect(() => {
    if (selectedFolder) {
      setChatMode("folders");
      setExpandedFolder(selectedFolder);
    }
  }, []);

  const fetchFolders = async () => {
    try {
      setLoadingFolders(true);
      const response = await fetch(`${API_BASE}/chats/folders`);
      if (response.ok) {
        const data = await response.json();
        setFolders(data.folders || []);
        setGeneralChatCount(data.general_chat_count || 0);
      }
    } catch (error) {
      console.error("Failed to fetch folders:", error);
    } finally {
      setLoadingFolders(false);
    }
  };

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

  const handleModeChange = (mode) => {
    setChatMode(mode);
    setShowModeDropdown(false);
    if (mode === "general") {
      onSelectFolder("");
      setExpandedFolder(null);
    }
  };

  const handleSelectFolder = (folderPath) => {
    if (expandedFolder === folderPath) {
      // Clicking same folder - collapse it
      setExpandedFolder(null);
      onSelectFolder("");
    } else {
      setExpandedFolder(folderPath);
      onSelectFolder(folderPath);
    }
  };

  const handleCreateNewFolder = () => {
    if (newFolderPath.trim()) {
      setChatMode("folders");
      setExpandedFolder(newFolderPath.trim());
      onSelectFolder(newFolderPath.trim());
      setShowNewFolderInput(false);
      setNewFolderPath("");
      fetchFolders();
    }
  };

  const getTimeAgo = (dateString) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getFolderDisplayName = (path) => {
    if (!path) return "General Chats";
    const parts = path.split(/[/\\]/);
    return parts[parts.length - 1] || path;
  };

  return (
    <div className="chat-list-container">
      {/* Header with Mode Dropdown */}
      <div className="chat-list-header">
        <div className="mode-selector">
          <button
            className="mode-dropdown-btn"
            onClick={() => setShowModeDropdown(!showModeDropdown)}
          >
            <div className="mode-icon">
              {chatMode === "general" ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
                </svg>
              )}
            </div>
            <span className="mode-label">
              {chatMode === "general" ? "General Chats" : "Folder Chats"}
            </span>
            <svg className="dropdown-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6,9 12,15 18,9" />
            </svg>
          </button>

          {showModeDropdown && (
            <div className="mode-dropdown-menu">
              <button
                className={`mode-option ${chatMode === "general" ? "active" : ""}`}
                onClick={() => handleModeChange("general")}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                </svg>
                <span>General Chats</span>
                <span className="mode-count">{generalChatCount}</span>
              </button>
              <button
                className={`mode-option ${chatMode === "folders" ? "active" : ""}`}
                onClick={() => handleModeChange("folders")}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
                </svg>
                <span>Folder Chats</span>
                <span className="mode-count">{folders.length}</span>
              </button>
            </div>
          )}
        </div>

        <button
          className="new-chat-btn"
          onClick={onCreateChat}
          title="New Chat"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </div>

      {/* Folders Section - Only shown when in folders mode */}
      {chatMode === "folders" && (
        <div className="folders-section">
          <div className="folders-header">
            <span>Folders</span>
            <button
              className="add-folder-btn"
              onClick={() => setShowNewFolderInput(!showNewFolderInput)}
              title="New Folder"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
          </div>

          {showNewFolderInput && (
            <div className="new-folder-input-section">
              <input
                type="text"
                className="new-folder-input"
                value={newFolderPath}
                onChange={(e) => setNewFolderPath(e.target.value)}
                placeholder="Folder path (e.g., projects/my-app)"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreateNewFolder();
                  if (e.key === "Escape") setShowNewFolderInput(false);
                }}
                autoFocus
              />
              <div className="new-folder-actions">
                <button className="btn-create" onClick={handleCreateNewFolder}>Create</button>
                <button className="btn-cancel" onClick={() => setShowNewFolderInput(false)}>Cancel</button>
              </div>
            </div>
          )}

          <div className="folders-list">
            {loadingFolders ? (
              <div className="folders-loading">Loading folders...</div>
            ) : folders.length === 0 ? (
              <div className="folders-empty-mini">No folders yet</div>
            ) : (
              folders.map((folder, index) => (
                <div
                  key={index}
                  className={`folder-item ${expandedFolder === folder.path ? "expanded" : ""}`}
                  onClick={() => handleSelectFolder(folder.path)}
                >
                  <div className="folder-item-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
                    </svg>
                  </div>
                  <div className="folder-item-info">
                    <span className="folder-item-name">{getFolderDisplayName(folder.path)}</span>
                    <span className="folder-item-meta">
                      {folder.chat_count} chat{folder.chat_count !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className={`folder-expand-icon ${expandedFolder === folder.path ? "expanded" : ""}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="6,9 12,15 18,9" />
                    </svg>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Current Folder Indicator */}
      {chatMode === "folders" && expandedFolder && (
        <div className="current-folder-bar">
          <span className="current-folder-label">In:</span>
          <span className="current-folder-name">{getFolderDisplayName(expandedFolder)}</span>
        </div>
      )}

      {/* Chat List */}
      <div className="chat-list">
        {loading && <div className="chat-list-loading">Loading chats...</div>}
        {!loading && (!chats || chats.length === 0) && (
          <div className="chat-list-empty">
            <div className="empty-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
              </svg>
            </div>
            <p>No chats yet</p>
            <span>Start a new conversation</span>
          </div>
        )}
        {chats &&
          chats.map((chat) => (
            <div
              key={chat.id}
              className={`chat-item ${selectedChatId === chat.id ? "active" : ""}`}
            >
              <button
                className="chat-item-content"
                onClick={() => onSelectChat(chat.id)}
              >
                <div className="chat-item-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                  </svg>
                </div>
                <div className="chat-item-info">
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
                    <>
                      <span className="chat-title">{chat.title || "Untitled Chat"}</span>
                      <span className="chat-time">{getTimeAgo(chat.updated_at)}</span>
                    </>
                  )}
                </div>
              </button>
              {selectedChatId === chat.id && (
                <div className="chat-item-actions">
                  {editingId === chat.id ? (
                    <>
                      <button className="action-btn save" onClick={() => saveEdit(chat.id)} title="Save">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="20,6 9,17 4,12" />
                        </svg>
                      </button>
                      <button className="action-btn cancel" onClick={cancelEdit} title="Cancel">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                      </button>
                    </>
                  ) : (
                    <>
                      <button className="action-btn edit" onClick={() => startEdit(chat)} title="Rename">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
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
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3,6 5,6 21,6" />
                          <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                        </svg>
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
