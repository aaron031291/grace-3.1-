import { useState } from "react";
import "./DiffViewer.css";

export default function DiffViewer({ diffData }) {
  const [searchQuery, setSearchQuery] = useState("");

  const getStatusColor = (status) => {
    const statusMap = {
      added: "#10b981",
      modified: "#3b82f6",
      deleted: "#ef4444",
      renamed: "#f59e0b",
    };
    return statusMap[status] || "#999";
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "added":
        return "+";
      case "deleted":
        return "-";
      case "modified":
        return "~";
      case "renamed":
        return ">";
      default:
        return "•";
    }
  };

  // Filter files based on search query
  const filteredFiles = diffData.files_changed.filter((file) =>
    file.path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="diff-viewer">
      <div className="diff-header">
        <h3>Changes</h3>
        <div className="diff-summary">
          <span className="diff-stat additions">
            +{diffData.stats.additions}
          </span>
          <span className="diff-stat deletions">
            -{diffData.stats.deletions}
          </span>
          <span className="diff-stat files">
            {diffData.stats.files_modified} files
          </span>
        </div>
      </div>

      <div className="diff-search">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          type="text"
          placeholder="Search files..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="diff-search-input"
        />
      </div>

      <div className="diff-content">
        {filteredFiles.length === 0 ? (
          <div className="diff-empty">
            {searchQuery
              ? "No files match your search"
              : "No changes in this commit"}
          </div>
        ) : (
          <div className="files-list">
            {filteredFiles.map((file, idx) => (
              <div key={idx} className="file-change">
                <div className="file-header">
                  <span
                    className="file-status"
                    style={{ borderLeftColor: getStatusColor(file.status) }}
                  >
                    <span className="status-icon">
                      {getStatusIcon(file.status)}
                    </span>
                    <span className="status-text">{file.status}</span>
                  </span>
                  <span className="file-path">{file.path}</span>
                </div>

                {(file.additions > 0 || file.deletions > 0) && (
                  <div className="file-stats">
                    {file.additions > 0 && (
                      <span className="stat-badge additions">
                        <span className="plus">+</span>
                        {file.additions}
                      </span>
                    )}
                    {file.deletions > 0 && (
                      <span className="stat-badge deletions">
                        <span className="minus">-</span>
                        {file.deletions}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <svg
        className="diff-background"
        viewBox="0 0 400 800"
        preserveAspectRatio="none"
      >
        <defs>
          <pattern
            id="diff-pattern"
            x="0"
            y="0"
            width="50"
            height="50"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="25" cy="25" r="1.5" fill="#333" opacity="0.3" />
          </pattern>
        </defs>
        <rect width="400" height="800" fill="url(#diff-pattern)" />
      </svg>
    </div>
  );
}
