/**
 * Ingestion Dashboard Component
 * ==============================
 * Real-time UI for the Librarian Ingestion Pipeline.
 * Shows data flow: Data -> Genesis Key -> Indexed -> Filed -> Memorized -> UI
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import './IngestionDashboard.css';
import { API_BASE_URL } from '../config/api';

const API_BASE = API_BASE_URL;

// Status icons and colors
const STATUS_CONFIG = {
  pending: { icon: '⏳', color: '#6b7280', label: 'Pending' },
  receiving: { icon: '📥', color: '#3b82f6', label: 'Receiving' },
  genesis_assigned: { icon: '🔑', color: '#8b5cf6', label: 'Genesis Key Assigned' },
  indexing: { icon: '🔍', color: '#f59e0b', label: 'Indexing' },
  indexed: { icon: '✓', color: '#10b981', label: 'Indexed' },
  filing: { icon: '📁', color: '#f59e0b', label: 'Filing' },
  filed: { icon: '✓', color: '#10b981', label: 'Filed' },
  memorizing: { icon: '🧠', color: '#ec4899', label: 'Memorizing' },
  complete: { icon: '✅', color: '#10b981', label: 'Complete' },
  failed: { icon: '❌', color: '#ef4444', label: 'Failed' }
};

// Content type icons
const TYPE_ICONS = {
  code: '💻',
  document: '📄',
  data: '📊',
  config: '⚙️',
  image: '🖼️',
  knowledge: '📚',
  log: '📋',
  unknown: '❓'
};

const IngestionDashboard = () => {
  const [ingestions, setIngestions] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [selectedIngestion, setSelectedIngestion] = useState(null);
  const [filter, setFilter] = useState({ status: '', contentType: '' });
  const [loading, setLoading] = useState(true);
  const [_error, _setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const eventSourceRef = useRef(null);
  const fileInputRef = useRef(null);

  // Fetch ingestions list
  const fetchIngestions = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filter.status) params.append('status', filter.status);
      if (filter.contentType) params.append('content_type', filter.contentType);
      params.append('limit', '50');

      const response = await fetch(`${API_BASE}/api/ingestion/list?${params}`);
      if (!response.ok) throw new Error('Failed to fetch ingestions');
      const data = await response.json();
      setIngestions(data.ingestions || []);
    } catch (err) {
      console.error('Error fetching ingestions:', err);
    }
  }, [filter]);

  // Fetch statistics
  const fetchStatistics = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/ingestion/statistics`);
      if (!response.ok) throw new Error('Failed to fetch statistics');
      const data = await response.json();
      setStatistics(data);
    } catch (err) {
      console.error('Error fetching statistics:', err);
    }
  }, []);

  // Fetch specific ingestion details
  const fetchIngestionDetails = useCallback(async (ingestionId) => {
    try {
      const response = await fetch(`${API_BASE}/api/ingestion/${ingestionId}`);
      if (!response.ok) throw new Error('Failed to fetch ingestion details');
      const data = await response.json();
      setSelectedIngestion(data);
    } catch (err) {
      console.error('Error fetching ingestion details:', err);
    }
  }, []);

  // Connect to SSE stream for real-time updates
  const connectToStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(`${API_BASE}/api/ingestion/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'statistics') {
        setStatistics(data.data);
      } else if (data.type === 'ingestion_update') {
        // Update the ingestion in the list
        setIngestions(prev => {
          const idx = prev.findIndex(i => i.ingestion_id === data.data.ingestion_id);
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = { ...updated[idx], ...data.data };
            return updated;
          } else {
            // Add new ingestion to the top
            return [data.data, ...prev].slice(0, 50);
          }
        });

        // Update selected ingestion if it matches
        if (selectedIngestion?.ingestion_id === data.data.ingestion_id) {
          setSelectedIngestion(prev => ({ ...prev, ...data.data }));
        }
      }
    };

    eventSource.onerror = () => {
      console.log('SSE connection error, reconnecting...');
      eventSource.close();
      setTimeout(connectToStream, 5000);
    };

    eventSourceRef.current = eventSource;
  }, [selectedIngestion]);

  // Initial data fetch
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchIngestions(), fetchStatistics()]);
      setLoading(false);
    };
    init();
  }, [fetchIngestions, fetchStatistics]);

  // Connect to SSE stream
  useEffect(() => {
    connectToStream();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connectToStream]);

  // Handle file upload
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress({ filename: file.name, status: 'uploading' });

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('metadata', JSON.stringify({ source: 'ui_upload' }));

      const response = await fetch(`${API_BASE}/api/ingestion/upload`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Upload failed');

      const result = await response.json();
      setUploadProgress({
        filename: file.name,
        status: 'complete',
        ingestion_id: result.ingestion_id,
        genesis_key: result.genesis_key
      });

      // Refresh the list
      await fetchIngestions();

      // Clear progress after a delay
      setTimeout(() => setUploadProgress(null), 3000);
    } catch (err) {
      setUploadProgress({
        filename: file.name,
        status: 'failed',
        error: err.message
      });
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Format file size
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="ingestion-dashboard loading">
        <div className="loading-spinner"></div>
        <p>Loading ingestion data...</p>
      </div>
    );
  }

  return (
    <div className="ingestion-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-title">
          <h2>📥 Librarian Ingestion Pipeline</h2>
          <p className="subtitle">Data Flow: Receive → Genesis Key → Index → File → Memorize</p>
        </div>
        <div className="header-actions">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
          <button
            className="upload-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? '📤 Uploading...' : '📤 Upload File'}
          </button>
          <button
            className="refresh-btn"
            onClick={() => {
              fetchIngestions();
              fetchStatistics();
            }}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Upload Progress */}
      {uploadProgress && (
        <div className={`upload-progress ${uploadProgress.status}`}>
          <span className="filename">{uploadProgress.filename}</span>
          <span className="status">
            {uploadProgress.status === 'uploading' && '⏳ Processing...'}
            {uploadProgress.status === 'complete' && `✅ Complete - ${uploadProgress.genesis_key}`}
            {uploadProgress.status === 'failed' && `❌ Failed: ${uploadProgress.error}`}
          </span>
        </div>
      )}

      {/* Statistics Cards */}
      {statistics && (
        <div className="statistics-cards">
          <div className="stat-card total">
            <div className="stat-icon">📊</div>
            <div className="stat-info">
              <div className="stat-value">{statistics.total_ingestions}</div>
              <div className="stat-label">Total Ingestions</div>
            </div>
          </div>
          <div className="stat-card size">
            <div className="stat-icon">💾</div>
            <div className="stat-info">
              <div className="stat-value">{statistics.total_size_mb} MB</div>
              <div className="stat-label">Total Size</div>
            </div>
          </div>
          <div className="stat-card complete">
            <div className="stat-icon">✅</div>
            <div className="stat-info">
              <div className="stat-value">{statistics.by_status?.complete || 0}</div>
              <div className="stat-label">Completed</div>
            </div>
          </div>
          <div className="stat-card failed">
            <div className="stat-icon">❌</div>
            <div className="stat-info">
              <div className="stat-value">{statistics.by_status?.failed || 0}</div>
              <div className="stat-label">Failed</div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="filters-bar">
        <select
          value={filter.status}
          onChange={(e) => setFilter(f => ({ ...f, status: e.target.value }))}
        >
          <option value="">All Statuses</option>
          {Object.entries(STATUS_CONFIG).map(([value, config]) => (
            <option key={value} value={value}>
              {config.icon} {config.label}
            </option>
          ))}
        </select>
        <select
          value={filter.contentType}
          onChange={(e) => setFilter(f => ({ ...f, contentType: e.target.value }))}
        >
          <option value="">All Types</option>
          {Object.entries(TYPE_ICONS).map(([value, icon]) => (
            <option key={value} value={value}>
              {icon} {value}
            </option>
          ))}
        </select>
      </div>

      {/* Main Content */}
      <div className="dashboard-content">
        {/* Ingestions List */}
        <div className="ingestions-list">
          <h3>Recent Ingestions</h3>
          {ingestions.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📭</div>
              <p>No ingestions yet</p>
              <p className="hint">Upload a file to get started</p>
            </div>
          ) : (
            <div className="ingestions-table">
              {ingestions.map(ing => {
                const statusConfig = STATUS_CONFIG[ing.status] || STATUS_CONFIG.pending;
                const typeIcon = TYPE_ICONS[ing.content_type] || '❓';

                return (
                  <div
                    key={ing.ingestion_id}
                    className={`ingestion-row ${selectedIngestion?.ingestion_id === ing.ingestion_id ? 'selected' : ''}`}
                    onClick={() => fetchIngestionDetails(ing.ingestion_id)}
                  >
                    <div className="row-icon" style={{ color: statusConfig.color }}>
                      {statusConfig.icon}
                    </div>
                    <div className="row-info">
                      <div className="row-filename">
                        <span className="type-icon">{typeIcon}</span>
                        {ing.filename}
                      </div>
                      <div className="row-meta">
                        <span className="genesis-key" title={ing.genesis_key}>
                          🔑 {ing.genesis_key?.substring(0, 12)}...
                        </span>
                        <span className="file-size">{formatSize(ing.file_size)}</span>
                      </div>
                    </div>
                    <div className="row-status" style={{ color: statusConfig.color }}>
                      {statusConfig.label}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Details Panel */}
        <div className="details-panel">
          {selectedIngestion ? (
            <>
              <h3>Ingestion Details</h3>
              <div className="details-content">
                {/* Basic Info */}
                <div className="detail-section">
                  <h4>📋 Basic Info</h4>
                  <div className="detail-row">
                    <span className="label">ID:</span>
                    <span className="value code">{selectedIngestion.ingestion_id}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Genesis Key:</span>
                    <span className="value code">{selectedIngestion.genesis_key}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Status:</span>
                    <span
                      className="value status-badge"
                      style={{
                        backgroundColor: STATUS_CONFIG[selectedIngestion.status]?.color,
                        color: 'white'
                      }}
                    >
                      {STATUS_CONFIG[selectedIngestion.status]?.icon} {STATUS_CONFIG[selectedIngestion.status]?.label}
                    </span>
                  </div>
                </div>

                {/* File Info */}
                <div className="detail-section">
                  <h4>📁 File Info</h4>
                  <div className="detail-row">
                    <span className="label">Filename:</span>
                    <span className="value">{selectedIngestion.filename}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Type:</span>
                    <span className="value">
                      {TYPE_ICONS[selectedIngestion.content_type]} {selectedIngestion.content_type}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Size:</span>
                    <span className="value">{formatSize(selectedIngestion.file_size)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Hash:</span>
                    <span className="value code">{selectedIngestion.content_hash?.substring(0, 16)}...</span>
                  </div>
                  {selectedIngestion.destination && (
                    <div className="detail-row">
                      <span className="label">Destination:</span>
                      <span className="value code" title={selectedIngestion.destination}>
                        {selectedIngestion.destination.split('/').slice(-3).join('/')}
                      </span>
                    </div>
                  )}
                </div>

                {/* IDs */}
                <div className="detail-section">
                  <h4>🔗 References</h4>
                  {selectedIngestion.index_id && (
                    <div className="detail-row">
                      <span className="label">Index ID:</span>
                      <span className="value code">{selectedIngestion.index_id}</span>
                    </div>
                  )}
                  {selectedIngestion.memory_id && (
                    <div className="detail-row">
                      <span className="label">Memory ID:</span>
                      <span className="value code">{selectedIngestion.memory_id}</span>
                    </div>
                  )}
                </div>

                {/* Timeline */}
                {selectedIngestion.timeline && selectedIngestion.timeline.length > 0 && (
                  <div className="detail-section">
                    <h4>⏱️ Timeline</h4>
                    <div className="timeline">
                      {selectedIngestion.timeline.map((event, idx) => {
                        const eventConfig = STATUS_CONFIG[event.status] || STATUS_CONFIG.pending;
                        return (
                          <div key={idx} className="timeline-event">
                            <div
                              className="event-icon"
                              style={{ backgroundColor: eventConfig.color }}
                            >
                              {eventConfig.icon}
                            </div>
                            <div className="event-content">
                              <div className="event-status">{eventConfig.label}</div>
                              <div className="event-message">{event.message}</div>
                              <div className="event-time">{formatTime(event.timestamp)}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Error */}
                {selectedIngestion.error && (
                  <div className="detail-section error">
                    <h4>❌ Error</h4>
                    <div className="error-message">{selectedIngestion.error}</div>
                  </div>
                )}

                {/* Timestamps */}
                <div className="detail-section">
                  <h4>📅 Timestamps</h4>
                  <div className="detail-row">
                    <span className="label">Created:</span>
                    <span className="value">{formatTime(selectedIngestion.created_at)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Updated:</span>
                    <span className="value">{formatTime(selectedIngestion.updated_at)}</span>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="no-selection">
              <div className="no-selection-icon">👆</div>
              <p>Select an ingestion to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Pipeline Flow Visualization */}
      <div className="pipeline-flow">
        <h3>🔄 Ingestion Pipeline Flow</h3>
        <div className="flow-steps">
          <div className="flow-step">
            <div className="step-icon">📥</div>
            <div className="step-label">Receive</div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step">
            <div className="step-icon">🔑</div>
            <div className="step-label">Genesis Key</div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step">
            <div className="step-icon">🔍</div>
            <div className="step-label">Index</div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step">
            <div className="step-icon">📁</div>
            <div className="step-label">File</div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step">
            <div className="step-icon">🧠</div>
            <div className="step-label">Memory</div>
          </div>
          <div className="flow-arrow">→</div>
          <div className="flow-step complete">
            <div className="step-icon">✅</div>
            <div className="step-label">Complete</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IngestionDashboard;
