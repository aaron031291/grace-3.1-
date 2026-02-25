import React, { useState, useEffect } from 'react';
import './ConnectorsTab.css';

const ConnectorsTab = () => {
  const [loading, setLoading] = useState(true);
  const [connectors, setConnectors] = useState([]);
  const [syncHistory, setSyncHistory] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [testingId, setTestingId] = useState(null);
  const [newConnector, setNewConnector] = useState({ name: '', type: 'github', url: '', auth_type: 'token', credentials: '' });

  const fetchConnectors = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/knowledge-base/connectors');
      if (response.ok) {
        const data = await response.json();
        setConnectors(data.connectors || []);
      } else {
        setConnectors([
          { id: 'c-1', name: 'GitHub Repos', type: 'github', url: 'https://github.com', status: 'connected', last_sync: '2025-01-11T10:00:00Z', documents: 245 },
          { id: 'c-2', name: 'Confluence Docs', type: 'confluence', url: 'https://company.atlassian.net', status: 'connected', last_sync: '2025-01-11T08:00:00Z', documents: 89 },
          { id: 'c-3', name: 'Notion Workspace', type: 'notion', url: 'https://notion.so', status: 'disconnected', last_sync: '2025-01-10T15:00:00Z', documents: 34 },
          { id: 'c-4', name: 'Google Drive', type: 'gdrive', url: 'https://drive.google.com', status: 'syncing', last_sync: '2025-01-11T09:30:00Z', documents: 156 },
        ]);
      }
    } catch (error) {
      console.error('Error fetching connectors:', error);
    }
    setLoading(false);
  };

  const fetchSyncHistory = async () => {
    try {
      const response = await fetch('/api/knowledge-base/sync-history');
      if (response.ok) {
        const data = await response.json();
        setSyncHistory(data.history || []);
      } else {
        setSyncHistory([
          { id: 's-1', connector: 'GitHub Repos', timestamp: '2025-01-11T10:00:00Z', status: 'success', documents: 12, duration: '45s' },
          { id: 's-2', connector: 'Google Drive', timestamp: '2025-01-11T09:30:00Z', status: 'in_progress', documents: 8, duration: '-' },
          { id: 's-3', connector: 'Confluence Docs', timestamp: '2025-01-11T08:00:00Z', status: 'success', documents: 5, duration: '32s' },
        ]);
      }
    } catch (error) {
      console.error('Error fetching sync history:', error);
    }
  };

  useEffect(() => {
    queueMicrotask(() => {
      fetchConnectors();
      fetchSyncHistory();
    });
  }, []);

  const handleAddConnector = async () => {
    try {
      await fetch('/api/knowledge-base/connectors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConnector),
      });
      setShowAddModal(false);
      setNewConnector({ name: '', type: 'github', url: '', auth_type: 'token', credentials: '' });
      fetchConnectors();
    } catch (error) {
      console.error('Error adding connector:', error);
    }
  };

  const handleTestConnection = async (connectorId) => {
    setTestingId(connectorId);
    try {
      await fetch(`/api/knowledge-base/connectors/${connectorId}/test`, { method: 'POST' });
      setTimeout(() => setTestingId(null), 2000);
    } catch (error) {
      console.error('Error testing connection:', error);
      setTestingId(null);
    }
  };

  const handleSync = async (connectorId) => {
    try {
      await fetch(`/api/knowledge-base/connectors/${connectorId}/sync`, { method: 'POST' });
      fetchConnectors();
      fetchSyncHistory();
    } catch (error) {
      console.error('Error syncing:', error);
    }
  };

  const handleDelete = async (connectorId) => {
    if (!window.confirm('Delete this connector?')) return;
    try {
      await fetch(`/api/knowledge-base/connectors/${connectorId}`, { method: 'DELETE' });
      fetchConnectors();
    } catch (error) {
      console.error('Error deleting:', error);
    }
  };

  const getTypeIcon = (type) => {
    const icons = { github: '🐙', confluence: '📘', notion: '📝', gdrive: '📁', slack: '💬', jira: '🎫' };
    return icons[type] || '🔗';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="connectors-tab">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading connectors...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="connectors-tab">
      <div className="connectors-header">
        <div className="header-left">
          <h2>Knowledge Connectors</h2>
          <p>Connect external knowledge sources</p>
        </div>
        <button className="btn-add" onClick={() => setShowAddModal(true)}>+ Add Connector</button>
      </div>

      <div className="connectors-content">
        <div className="connectors-grid">
          {connectors.map((connector) => (
            <div key={connector.id} className={`connector-card status-${connector.status}`}>
              <div className="connector-icon">{getTypeIcon(connector.type)}</div>
              <div className="connector-info">
                <h4>{connector.name}</h4>
                <span className="connector-url">{connector.url}</span>
              </div>
              <div className={`connector-status status-${connector.status}`}>
                {connector.status === 'syncing' && <span className="sync-spinner"></span>}
                {connector.status}
              </div>
              <div className="connector-stats">
                <span>{connector.documents} docs</span>
                <span>Last: {formatDate(connector.last_sync)}</span>
              </div>
              <div className="connector-actions">
                <button className="btn-test" onClick={() => handleTestConnection(connector.id)} disabled={testingId === connector.id}>
                  {testingId === connector.id ? 'Testing...' : 'Test'}
                </button>
                <button className="btn-sync" onClick={() => handleSync(connector.id)} disabled={connector.status === 'syncing'}>
                  Sync
                </button>
                <button className="btn-delete" onClick={() => handleDelete(connector.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>

        <div className="sync-history">
          <h4>Recent Sync Activity</h4>
          <div className="history-list">
            {syncHistory.map((sync) => (
              <div key={sync.id} className={`history-item status-${sync.status}`}>
                <span className="history-connector">{sync.connector}</span>
                <span className="history-time">{formatDate(sync.timestamp)}</span>
                <span className={`history-status status-${sync.status}`}>{sync.status}</span>
                <span className="history-docs">{sync.documents} docs</span>
                <span className="history-duration">{sync.duration}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Connector</h3>
              <button className="modal-close" onClick={() => setShowAddModal(false)}>×</button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); handleAddConnector(); }}>
              <div className="form-group">
                <label>Name</label>
                <input type="text" value={newConnector.name} onChange={(e) => setNewConnector({ ...newConnector, name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={newConnector.type} onChange={(e) => setNewConnector({ ...newConnector, type: e.target.value })}>
                  <option value="github">GitHub</option>
                  <option value="confluence">Confluence</option>
                  <option value="notion">Notion</option>
                  <option value="gdrive">Google Drive</option>
                  <option value="slack">Slack</option>
                  <option value="jira">Jira</option>
                </select>
              </div>
              <div className="form-group">
                <label>URL</label>
                <input type="url" value={newConnector.url} onChange={(e) => setNewConnector({ ...newConnector, url: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>API Token / Credentials</label>
                <input type="password" value={newConnector.credentials} onChange={(e) => setNewConnector({ ...newConnector, credentials: e.target.value })} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowAddModal(false)}>Cancel</button>
                <button type="submit" className="btn-submit">Add Connector</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConnectorsTab;
