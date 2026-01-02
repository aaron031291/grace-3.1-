import { useState, useEffect } from "react";
import "./FileBrowser.css";

export default function FileBrowser({ onOpenVSCode, onPathChange }) {
  const [currentPath, setCurrentPath] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [showNewFolderInput, setShowNewFolderInput] = useState(false);
  const [uploading, setUploading] = useState(false);
  const API_BASE = "http://localhost:8000";

  // Load directory on mount and when path changes
  useEffect(() => {
    loadDirectory();
    // Notify parent of path change
    if (onPathChange) {
      onPathChange(currentPath);
    }
  }, [currentPath]);

  const loadDirectory = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/files/browse?path=${encodeURIComponent(currentPath)}`
      );
      if (!response.ok) throw new Error("Failed to load directory");
      const data = await response.json();
      setItems(data.items || []);
    } catch (err) {
      setError(err.message);
      console.error("Load directory error:", err);
    } finally {
      setLoading(false);
    }
  };

  const navigateTo = (path) => {
    setCurrentPath(path);
  };

  const goBack = () => {
    const parts = currentPath.split("/").filter((p) => p);
    parts.pop();
    setCurrentPath(parts.join("/"));
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) {
      setError("Folder name cannot be empty");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const folderPath = currentPath
        ? `${currentPath}/${newFolderName}`
        : newFolderName;

      const response = await fetch(
        `${API_BASE}/files/create-folder?path=${encodeURIComponent(
          folderPath
        )}`,
        {
          method: "POST",
        }
      );

      if (!response.ok) throw new Error("Failed to create folder");

      setNewFolderName("");
      setShowNewFolderInput(false);
      await loadDirectory();
    } catch (err) {
      setError(err.message);
      console.error("Create folder error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("folder_path", currentPath);
      formData.append("ingest", "true");
      formData.append("source_type", "user_generated");

      const response = await fetch(`${API_BASE}/files/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");
      const data = await response.json();

      if (data.success) {
        setError(null);
        await loadDirectory();
        // Reset file input
        e.target.value = "";
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError(err.message);
      console.error("Upload error:", err);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteFile = async (filePath) => {
    if (!confirm(`Delete ${filePath}?`)) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/files/delete?file_path=${encodeURIComponent(
          filePath
        )}&delete_from_db=true`,
        { method: "DELETE" }
      );

      if (!response.ok) throw new Error("Delete failed");
      await loadDirectory();
    } catch (err) {
      setError(err.message);
      console.error("Delete error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteFolder = async (folderPath) => {
    if (!confirm(`Delete folder "${folderPath}" and all its contents?`)) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/files/delete-folder?folder_path=${encodeURIComponent(
          folderPath
        )}`,
        { method: "DELETE" }
      );

      if (!response.ok) throw new Error("Delete failed");
      await loadDirectory();
    } catch (err) {
      setError(err.message);
      console.error("Delete folder error:", err);
    } finally {
      setLoading(false);
    }
  };

  const getBreadcrumbs = () => {
    const parts = currentPath.split("/").filter((p) => p);
    const breadcrumbs = [];

    breadcrumbs.push(
      <button key="root" className="breadcrumb" onClick={() => navigateTo("")}>
        📁 Knowledge Base
      </button>
    );

    let path = "";
    for (const part of parts) {
      path = path ? `${path}/${part}` : part;
      breadcrumbs.push(
        <span key={`sep-${path}`} className="breadcrumb-sep">
          /
        </span>
      );
      breadcrumbs.push(
        <button
          key={path}
          className="breadcrumb"
          onClick={() => navigateTo(path)}
        >
          {part}
        </button>
      );
    }

    return breadcrumbs;
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  return (
    <div className="file-browser">
      <div className="browser-header">
        <div className="header-top">
          <h2>Knowledge Base</h2>
          <div className="header-actions">
            <button
              className="icon-button vscode-button"
              onClick={() => {
                if (onOpenVSCode) {
                  onOpenVSCode(currentPath);
                }
              }}
              title="Open VS Code in current folder"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                {/* VS Code logo */}
                <path d="M23.15 2.587L18.21.21a1.494 1.494 0 0 0-1.705.29l-9.46 8.63-4.12-3.128a.999.999 0 0 0-1.276.057L.987 7.644A.999.999 0 0 0 .934 8.85L3.542 11.9.934 15.15a.999.999 0 0 0 .053 1.206l1.661 1.605a.999.999 0 0 0 1.276.057l4.12-3.128 9.46 8.63a1.49 1.49 0 0 0 1.704.29l4.942-2.377A1.5 1.5 0 0 0 24 20.06V3.54A1.5 1.5 0 0 0 23.15 2.587z" />
              </svg>
            </button>
            <label className="upload-button">
              <input
                type="file"
                onChange={handleFileUpload}
                disabled={uploading}
                accept=".txt,.md,.pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt"
              />
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              {uploading ? "Uploading..." : "Upload"}
            </label>
            <button
              className="icon-button"
              onClick={() => setShowNewFolderInput(!showNewFolderInput)}
              title="New Folder"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                <line x1="12" y1="11" x2="12" y2="17" />
                <line x1="9" y1="14" x2="15" y2="14" />
              </svg>
            </button>
            {currentPath && (
              <button className="icon-button" onClick={goBack} title="Back">
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
              </button>
            )}
            <button
              className="icon-button"
              onClick={loadDirectory}
              disabled={loading}
              title="Refresh"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <polyline points="23 4 23 10 17 10" />
                <polyline points="1 20 1 14 7 14" />
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36M20.49 15a9 9 0 0 1-14.85 3.36" />
              </svg>
            </button>
          </div>
        </div>
        <div className="breadcrumbs">{getBreadcrumbs()}</div>
      </div>

      {error && (
        <div className="error-message">
          <div className="error-content">
            <strong>Error:</strong> {error}
          </div>
          <button className="error-close" onClick={() => setError(null)}>
            ×
          </button>
        </div>
      )}

      {showNewFolderInput && (
        <div className="new-folder-input">
          <input
            type="text"
            placeholder="Folder name"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === "Enter") handleCreateFolder();
            }}
            autoFocus
          />
          <button
            className="btn-small btn-primary"
            onClick={handleCreateFolder}
            disabled={loading}
          >
            Create
          </button>
          <button
            className="btn-small btn-secondary"
            onClick={() => {
              setShowNewFolderInput(false);
              setNewFolderName("");
            }}
          >
            Cancel
          </button>
        </div>
      )}

      <div className="items-container">
        <div className="items-list">
          {items.length === 0 ? (
            <div className="empty-state">
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                className="empty-icon"
              >
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
              <p className="empty-title">This folder is empty</p>
              <p className="empty-subtitle">
                Upload files or create folders to get started
              </p>
            </div>
          ) : (
            <div className="items-table">
              {items.map((item) => (
                <div
                  key={item.path}
                  className={`file-row ${item.type}`}
                  onDoubleClick={
                    item.type === "folder"
                      ? () => navigateTo(item.path)
                      : undefined
                  }
                >
                  <div className="file-icon-col">
                    {item.type === "folder" ? (
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        className="icon-folder"
                      >
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                      </svg>
                    ) : (
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        className="icon-file"
                      >
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                        <polyline points="13 2 13 9 20 9" />
                      </svg>
                    )}
                  </div>
                  <div className="file-name-col">
                    {item.type === "folder" ? (
                      <button
                        className="file-link"
                        onClick={() => navigateTo(item.path)}
                      >
                        {item.name}
                      </button>
                    ) : (
                      <span className="file-name">{item.name}</span>
                    )}
                  </div>
                  <div className="file-type-col">
                    {item.type === "folder" ? (
                      <span className="file-type-badge">Folder</span>
                    ) : (
                      <span className="file-type-badge">
                        {item.extension
                          ? item.extension.substring(1).toUpperCase()
                          : "File"}
                      </span>
                    )}
                  </div>
                  <div className="file-size-col">
                    {item.size ? formatFileSize(item.size) : "—"}
                  </div>
                  <div className="file-actions-col">
                    {item.type === "file" && (
                      <button
                        className="action-btn"
                        onClick={() => handleDeleteFile(item.path)}
                        title="Delete file"
                      >
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M10 11v6M14 11v6" />
                        </svg>
                      </button>
                    )}
                    {item.type === "folder" && (
                      <button
                        className="action-btn"
                        onClick={() => handleDeleteFolder(item.path)}
                        title="Delete folder"
                      >
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M10 11v6M14 11v6" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
