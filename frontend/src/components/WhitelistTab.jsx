import React, { useState, useEffect } from 'react';
import './WhitelistTab.css';

const WhitelistTab = () => {
  const [view, setView] = useState('overview'); // overview, domains, paths, patterns, logs
  const [loading, setLoading] = useState(true);
  const [whitelistData, setWhitelistData] = useState(null);
  const [domains, setDomains] = useState([]);
  const [paths, setPaths] = useState([]);
  const [patterns, setPatterns] = useState([]);
  const [logs, setLogs] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addType, setAddType] = useState('domain');
  const [newEntry, setNewEntry] = useState({ value: '', description: '', priority: 'medium' });

  useEffect(() => {
    fetchWhitelistData();
  }, []);

  const fetchWhitelistData = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/layer1/whitelist');
      if (response.ok) {
        const data = await response.json();
        setWhitelistData(data);
        setDomains(data.domains || []);
        setPaths(data.paths || []);
        setPatterns(data.patterns || []);
      } else {
        // Demo data
        setWhitelistData({
          total_entries: 156,
          domains_count: 45,
          paths_count: 68,
          patterns_count: 43,
          last_updated: '2025-01-11T10:30:00Z',
          blocked_today: 12,
          allowed_today: 892,
        });
        setDomains([
          { id: 'd-1', domain: 'github.com', status: 'active', added: '2025-01-01', hits: 245, description: 'GitHub API access' },
          { id: 'd-2', domain: 'api.openai.com', status: 'active', added: '2025-01-02', hits: 189, description: 'OpenAI API' },
          { id: 'd-3', domain: 'huggingface.co', status: 'active', added: '2025-01-03', hits: 67, description: 'Hugging Face models' },
          { id: 'd-4', domain: 'arxiv.org', status: 'active', added: '2025-01-05', hits: 34, description: 'Research papers' },
          { id: 'd-5', domain: 'pypi.org', status: 'paused', added: '2025-01-08', hits: 12, description: 'Python packages' },
        ]);
        setPaths([
          { id: 'p-1', path: '/api/*', type: 'wildcard', status: 'active', hits: 1250, description: 'All API endpoints' },
          { id: 'p-2', path: '/auth/login', type: 'exact', status: 'active', hits: 450, description: 'Login endpoint' },
          { id: 'p-3', path: '/data/export/*', type: 'wildcard', status: 'active', hits: 89, description: 'Data export paths' },
          { id: 'p-4', path: '/admin/*', type: 'wildcard', status: 'restricted', hits: 23, description: 'Admin paths' },
        ]);
        setPatterns([
          { id: 'pt-1', pattern: '^[a-zA-Z0-9_]+\\.py$', type: 'regex', status: 'active', hits: 890, description: 'Python files' },
          { id: 'pt-2', pattern: '^test_.*', type: 'regex', status: 'active', hits: 234, description: 'Test files' },
          { id: 'pt-3', pattern: '*.md', type: 'glob', status: 'active', hits: 156, description: 'Markdown files' },
          { id: 'pt-4', pattern: 'config.*', type: 'glob', status: 'active', hits: 45, description: 'Config files' },
        ]);
      }
    } catch (error) {
      console.error('Error fetching whitelist:', error);
    }
    setLoading(false);
  };

  const fetchLogs = async () => {
    try {
      const response = await fetch('/api/layer1/whitelist/logs');
      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
      } else {
        setLogs([
          { id: 'l-1', timestamp: '2025-01-11T10:28:00Z', action: 'allowed', type: 'domain', value: 'github.com', source: 'API request' },
          { id: 'l-2', timestamp: '2025-01-11T10:27:00Z', action: 'blocked', type: 'path', value: '/admin/delete', source: 'User input' },
          { id: 'l-3', timestamp: '2025-01-11T10:25:00Z', action: 'allowed', type: 'pattern', value: 'utils.py', source: 'File access' },
          { id: 'l-4', timestamp: '2025-01-11T10:22:00Z', action: 'allowed', type: 'domain', value: 'api.openai.com', source: 'LLM request' },
          { id: 'l-5', timestamp: '2025-01-11T10:20:00Z', action: 'blocked', type: 'domain', value: 'malicious.com', source: 'External API' },
        ]);
      }
    } catch (error) {
      console.error('Error fetching logs:', error);
    }
  };

  const handleAddEntry = async () => {
    try {
      await fetch('/api/layer1/whitelist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: addType, ...newEntry }),
      });
      setShowAddModal(false);
      setNewEntry({ value: '', description: '', priority: 'medium' });
      fetchWhitelistData();
    } catch (error) {
      console.error('Error adding entry:', error);
    }
  };

  const handleToggleStatus = async (type, id, currentStatus) => {
    const newStatus = currentStatus === 'active' ? 'paused' : 'active';
    try {
      await fetch(`/api/layer1/whitelist/${type}/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      fetchWhitelistData();
    } catch (error) {
      console.error('Error toggling status:', error);
    }
  };

  const handleDelete = async (type, id) => {
    if (!window.confirm('Are you sure you want to delete this entry?')) return;
    try {
      await fetch(`/api/layer1/whitelist/${type}/${id}`, { method: 'DELETE' });
      fetchWhitelistData();
    } catch (error) {
      console.error('Error deleting entry:', error);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return (
      <div className="whitelist-tab">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading whitelist...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="whitelist-tab">
      <div className="whitelist-header">
        <div className="header-left">
          <h2>Whitelist Management</h2>
          <p>Control allowed domains, paths, and patterns</p>
        </div>
        <div className="header-stats">
          {whitelistData && (
            <>
              <div className="stat-item">
                <span className="stat-value">{whitelistData.total_entries}</span>
                <span className="stat-label">Total Entries</span>
              </div>
              <div className="stat-item allowed">
                <span className="stat-value">{whitelistData.allowed_today}</span>
                <span className="stat-label">Allowed Today</span>
              </div>
              <div className="stat-item blocked">
                <span className="stat-value">{whitelistData.blocked_today}</span>
                <span className="stat-label">Blocked Today</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="whitelist-toolbar">
        <div className="view-tabs">
          <button className={view === 'overview' ? 'active' : ''} onClick={() => setView('overview')}>
            Overview
          </button>
          <button className={view === 'domains' ? 'active' : ''} onClick={() => setView('domains')}>
            Domains ({domains.length})
          </button>
          <button className={view === 'paths' ? 'active' : ''} onClick={() => setView('paths')}>
            Paths ({paths.length})
          </button>
          <button className={view === 'patterns' ? 'active' : ''} onClick={() => setView('patterns')}>
            Patterns ({patterns.length})
          </button>
          <button className={view === 'logs' ? 'active' : ''} onClick={() => { setView('logs'); fetchLogs(); }}>
            Logs
          </button>
        </div>
        <button className="btn-add" onClick={() => setShowAddModal(true)}>
          + Add Entry
        </button>
      </div>

      <div className="whitelist-content">
        {/* Overview View */}
        {view === 'overview' && whitelistData && (
          <div className="overview-view">
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon">🌐</div>
                <div className="stat-info">
                  <span className="stat-value">{whitelistData.domains_count}</span>
                  <span className="stat-label">Domains</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">📁</div>
                <div className="stat-info">
                  <span className="stat-value">{whitelistData.paths_count}</span>
                  <span className="stat-label">Paths</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">🔍</div>
                <div className="stat-info">
                  <span className="stat-value">{whitelistData.patterns_count}</span>
                  <span className="stat-label">Patterns</span>
                </div>
              </div>
            </div>

            <div className="recent-activity">
              <h4>Recent Top Hits</h4>
              <div className="activity-list">
                {domains.slice(0, 3).map((d) => (
                  <div key={d.id} className="activity-item">
                    <span className="activity-type">🌐</span>
                    <span className="activity-value">{d.domain}</span>
                    <span className="activity-hits">{d.hits} hits</span>
                  </div>
                ))}
                {paths.slice(0, 2).map((p) => (
                  <div key={p.id} className="activity-item">
                    <span className="activity-type">📁</span>
                    <span className="activity-value">{p.path}</span>
                    <span className="activity-hits">{p.hits} hits</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="quick-actions">
              <h4>Quick Actions</h4>
              <div className="action-buttons">
                <button onClick={() => { setAddType('domain'); setShowAddModal(true); }}>
                  + Add Domain
                </button>
                <button onClick={() => { setAddType('path'); setShowAddModal(true); }}>
                  + Add Path
                </button>
                <button onClick={() => { setAddType('pattern'); setShowAddModal(true); }}>
                  + Add Pattern
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Domains View */}
        {view === 'domains' && (
          <div className="list-view">
            <div className="list-header">
              <h4>Whitelisted Domains</h4>
            </div>
            <div className="entries-list">
              {domains.map((domain) => (
                <div key={domain.id} className={`entry-card status-${domain.status}`}>
                  <div className="entry-icon">🌐</div>
                  <div className="entry-info">
                    <span className="entry-value">{domain.domain}</span>
                    <span className="entry-description">{domain.description}</span>
                  </div>
                  <div className="entry-stats">
                    <span className="entry-hits">{domain.hits} hits</span>
                    <span className="entry-date">Added: {formatDate(domain.added)}</span>
                  </div>
                  <div className={`entry-status status-${domain.status}`}>{domain.status}</div>
                  <div className="entry-actions">
                    <button
                      className="btn-toggle"
                      onClick={() => handleToggleStatus('domains', domain.id, domain.status)}
                    >
                      {domain.status === 'active' ? 'Pause' : 'Activate'}
                    </button>
                    <button className="btn-delete" onClick={() => handleDelete('domains', domain.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Paths View */}
        {view === 'paths' && (
          <div className="list-view">
            <div className="list-header">
              <h4>Whitelisted Paths</h4>
            </div>
            <div className="entries-list">
              {paths.map((path) => (
                <div key={path.id} className={`entry-card status-${path.status}`}>
                  <div className="entry-icon">📁</div>
                  <div className="entry-info">
                    <span className="entry-value">{path.path}</span>
                    <span className="entry-description">{path.description}</span>
                  </div>
                  <div className="entry-type-badge">{path.type}</div>
                  <div className="entry-stats">
                    <span className="entry-hits">{path.hits} hits</span>
                  </div>
                  <div className={`entry-status status-${path.status}`}>{path.status}</div>
                  <div className="entry-actions">
                    <button
                      className="btn-toggle"
                      onClick={() => handleToggleStatus('paths', path.id, path.status)}
                    >
                      {path.status === 'active' ? 'Pause' : 'Activate'}
                    </button>
                    <button className="btn-delete" onClick={() => handleDelete('paths', path.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Patterns View */}
        {view === 'patterns' && (
          <div className="list-view">
            <div className="list-header">
              <h4>Whitelisted Patterns</h4>
            </div>
            <div className="entries-list">
              {patterns.map((pattern) => (
                <div key={pattern.id} className={`entry-card status-${pattern.status}`}>
                  <div className="entry-icon">🔍</div>
                  <div className="entry-info">
                    <code className="entry-value">{pattern.pattern}</code>
                    <span className="entry-description">{pattern.description}</span>
                  </div>
                  <div className="entry-type-badge">{pattern.type}</div>
                  <div className="entry-stats">
                    <span className="entry-hits">{pattern.hits} hits</span>
                  </div>
                  <div className={`entry-status status-${pattern.status}`}>{pattern.status}</div>
                  <div className="entry-actions">
                    <button
                      className="btn-toggle"
                      onClick={() => handleToggleStatus('patterns', pattern.id, pattern.status)}
                    >
                      {pattern.status === 'active' ? 'Pause' : 'Activate'}
                    </button>
                    <button className="btn-delete" onClick={() => handleDelete('patterns', pattern.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Logs View */}
        {view === 'logs' && (
          <div className="logs-view">
            <div className="list-header">
              <h4>Access Logs</h4>
              <button className="btn-refresh" onClick={fetchLogs}>Refresh</button>
            </div>
            <div className="logs-list">
              {logs.map((log) => (
                <div key={log.id} className={`log-entry action-${log.action}`}>
                  <span className="log-time">{formatTime(log.timestamp)}</span>
                  <span className={`log-action action-${log.action}`}>{log.action}</span>
                  <span className="log-type">{log.type}</span>
                  <span className="log-value">{log.value}</span>
                  <span className="log-source">{log.source}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Whitelist Entry</h3>
              <button className="modal-close" onClick={() => setShowAddModal(false)}>×</button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); handleAddEntry(); }}>
              <div className="form-group">
                <label>Type</label>
                <select value={addType} onChange={(e) => setAddType(e.target.value)}>
                  <option value="domain">Domain</option>
                  <option value="path">Path</option>
                  <option value="pattern">Pattern</option>
                </select>
              </div>
              <div className="form-group">
                <label>Value</label>
                <input
                  type="text"
                  value={newEntry.value}
                  onChange={(e) => setNewEntry({ ...newEntry, value: e.target.value })}
                  placeholder={addType === 'domain' ? 'example.com' : addType === 'path' ? '/api/*' : '*.py'}
                  required
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <input
                  type="text"
                  value={newEntry.description}
                  onChange={(e) => setNewEntry({ ...newEntry, description: e.target.value })}
                  placeholder="Brief description..."
                />
              </div>
              <div className="form-group">
                <label>Priority</label>
                <select value={newEntry.priority} onChange={(e) => setNewEntry({ ...newEntry, priority: e.target.value })}>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit">
                  Add Entry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default WhitelistTab;
