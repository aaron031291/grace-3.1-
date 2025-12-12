import { useState, useRef, useEffect } from "react";
import "./RAGTab.css";

export default function RAGTab() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [activeTab, setActiveTab] = useState("documents"); // documents, search, upload
  const fileInputRef = useRef(null);

  const API_BASE = "http://localhost:8000";

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  // Load documents list
  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/ingest/documents`);
      if (!response.ok) throw new Error("Failed to load documents");
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (err) {
      setError(err.message);
      console.error("Load documents error:", err);
    } finally {
      setLoading(false);
    }
  };

  // Handle file upload
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("source", "ui-upload");

      const response = await fetch(`${API_BASE}/ingest/file`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");
      const data = await response.json();

      if (data.success) {
        setError(null);
        await loadDocuments(); // Reload documents list
        setActiveTab("documents"); // Switch to documents tab
        if (fileInputRef.current) fileInputRef.current.value = "";
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

  // Handle paste text
  const handlePasteText = async () => {
    const textInput = document.getElementById("text-input");
    const filenameInput = document.getElementById("filename-input");

    if (!textInput?.value || !filenameInput?.value) {
      setError("Please enter both text and filename");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/ingest/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: textInput.value,
          filename: filenameInput.value,
          source: "ui-paste",
        }),
      });

      if (!response.ok) throw new Error("Upload failed");
      const data = await response.json();

      if (data.success) {
        setError(null);
        await loadDocuments();
        setActiveTab("documents");
        textInput.value = "";
        filenameInput.value = "";
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError(err.message);
      console.error("Paste text error:", err);
    } finally {
      setUploading(false);
    }
  };

  // Handle search
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setError("Please enter a search query");
      return;
    }

    setSearching(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/ingest/search?query=${encodeURIComponent(
          searchQuery
        )}&limit=10`,
        { method: "POST" }
      );

      if (!response.ok) throw new Error("Search failed");
      const data = await response.json();
      setSearchResults(data.results || []);
    } catch (err) {
      setError(err.message);
      console.error("Search error:", err);
    } finally {
      setSearching(false);
    }
  };

  // Delete document
  const deleteDocument = async (docId) => {
    if (!confirm("Delete this document?")) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/ingest/documents/${docId}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("Delete failed");
      await loadDocuments();
    } catch (err) {
      setError(err.message);
      console.error("Delete error:", err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "completed":
        return "#10b981";
      case "processing":
        return "#f59e0b";
      case "pending":
        return "#6b7280";
      case "failed":
        return "#ef4444";
      default:
        return "#6b7280";
    }
  };

  return (
    <div className="rag-tab">
      <div className="rag-container">
        {/* Tabs */}
        <div className="rag-tabs">
          <button
            className={`tab-button ${
              activeTab === "documents" ? "active" : ""
            }`}
            onClick={() => setActiveTab("documents")}
          >
            <span className="tab-icon">📄</span>
            Documents
          </button>
          <button
            className={`tab-button ${activeTab === "search" ? "active" : ""}`}
            onClick={() => setActiveTab("search")}
          >
            <span className="tab-icon">🔍</span>
            Search
          </button>
          <button
            className={`tab-button ${activeTab === "upload" ? "active" : ""}`}
            onClick={() => setActiveTab("upload")}
          >
            <span className="tab-icon">⬆️</span>
            Upload
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <strong>Error:</strong> {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === "documents" && (
          <div className="tab-content documents-tab">
            <div className="documents-header">
              <h2>Ingested Documents</h2>
              <button
                className="refresh-button"
                onClick={loadDocuments}
                disabled={loading}
              >
                {loading ? "Loading..." : "🔄 Refresh"}
              </button>
            </div>

            {documents.length === 0 ? (
              <div className="empty-state">
                <p>No documents uploaded yet</p>
                <p className="hint">Upload documents to get started with RAG</p>
              </div>
            ) : (
              <div className="documents-list">
                {documents.map((doc) => (
                  <div key={doc.id} className="document-card">
                    <div className="doc-header">
                      <div className="doc-title">
                        <h3>{doc.filename}</h3>
                        <span
                          className="status-badge"
                          style={{
                            backgroundColor: getStatusColor(doc.status),
                          }}
                        >
                          {doc.status}
                        </span>
                      </div>
                      <button
                        className="delete-btn"
                        onClick={() => deleteDocument(doc.id)}
                        title="Delete document"
                      >
                        🗑️
                      </button>
                    </div>
                    <div className="doc-info">
                      <div className="info-row">
                        <span className="label">Source:</span>
                        <span>{doc.source}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">Chunks:</span>
                        <span>{doc.total_chunks}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">Size:</span>
                        <span>{(doc.text_length / 1024).toFixed(2)} KB</span>
                      </div>
                      <div className="info-row">
                        <span className="label">Added:</span>
                        <span>
                          {new Date(doc.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Search Tab */}
        {activeTab === "search" && (
          <div className="tab-content search-tab">
            <h2>Search Documents</h2>
            <form onSubmit={handleSearch} className="search-form">
              <div className="search-input-group">
                <input
                  type="text"
                  placeholder="Enter search query..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  disabled={searching}
                  className="search-input"
                />
                <button
                  type="submit"
                  disabled={searching}
                  className="search-button"
                >
                  {searching ? "Searching..." : "🔍 Search"}
                </button>
              </div>
            </form>

            {searchResults.length === 0 && !searching && (
              <div className="empty-state">
                <p>No search results yet</p>
                <p className="hint">
                  Enter a query to search through documents
                </p>
              </div>
            )}

            {searchResults.length > 0 && (
              <div className="search-results">
                <p className="results-count">
                  Found {searchResults.length} matching chunks
                </p>
                {searchResults.map((result, idx) => (
                  <div key={idx} className="search-result-card">
                    <div className="result-header">
                      <span className="score">
                        Score: {(result.score * 100).toFixed(0)}%
                      </span>
                      <span className="doc-ref">
                        {result.metadata?.filename ||
                          `Document ${result.document_id}`}
                      </span>
                    </div>
                    <p className="result-text">{result.text}</p>
                    <div className="result-meta">
                      <span>Chunk {result.chunk_index}</span>
                      <span>Doc ID: {result.document_id}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Upload Tab */}
        {activeTab === "upload" && (
          <div className="tab-content upload-tab">
            <h2>Upload Documents</h2>

            {/* File Upload Section */}
            <div className="upload-section">
              <h3>Upload Text File</h3>
              <div className="file-upload-area">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.md,.pdf"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  id="file-input"
                  className="file-input-hidden"
                />
                <label htmlFor="file-input" className="file-upload-label">
                  <div className="upload-icon">📁</div>
                  <p>Click to upload or drag and drop</p>
                  <p className="file-hint">TXT, MD, PDF (up to 10MB)</p>
                </label>
              </div>
            </div>

            {/* Text Paste Section */}
            <div className="upload-section">
              <h3>Paste Text Content</h3>
              <input
                type="text"
                id="filename-input"
                placeholder="Enter filename (e.g., notes.txt)"
                className="text-input"
                disabled={uploading}
              />
              <textarea
                id="text-input"
                placeholder="Paste or type your text content here..."
                className="text-area"
                rows="8"
                disabled={uploading}
              />
              <button
                onClick={handlePasteText}
                disabled={uploading}
                className="submit-button"
              >
                {uploading ? "Uploading..." : "⬆️ Upload Text"}
              </button>
            </div>

            <div className="upload-info">
              <p>
                <strong>Note:</strong> Uploaded documents are automatically
                chunked and indexed for semantic search.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
