import React, { useState, useEffect } from 'react';
import './GenesisKeyTab.css';

const GenesisKeyTab = () => {
  const [view, setView] = useState('dashboard'); // dashboard, keys, archives, curation, analysis
  const [loading, setLoading] = useState(true);
  const [genesisKeys, setGenesisKeys] = useState([]);
  const [selectedKey, setSelectedKey] = useState(null);
  const [archives, setArchives] = useState([]);
  const [curationStatus, setCurationStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [dailySummary, setDailySummary] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);

  useEffect(() => {
    fetchStats();
    fetchGenesisKeys();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/genesis/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      } else {
        // Demo stats
        setStats({
          total_keys: 1247,
          active_keys: 892,
          archived_keys: 355,
          keys_today: 23,
          keys_this_week: 156,
          coverage_percentage: 87.5,
          health_score: 0.92,
        });
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
      setStats({
        total_keys: 1247,
        active_keys: 892,
        archived_keys: 355,
        keys_today: 23,
        keys_this_week: 156,
        coverage_percentage: 87.5,
        health_score: 0.92,
      });
    }
    setLoading(false);
  };

  const fetchGenesisKeys = async () => {
    try {
      const response = await fetch('/api/genesis/keys');
      if (response.ok) {
        const data = await response.json();
        setGenesisKeys(data.keys || []);
      } else {
        // Demo keys
        setGenesisKeys([
          {
            id: 'gk-001',
            key: 'GK-2025-0111-API-001',
            type: 'file',
            path: 'backend/api/librarian_api.py',
            created_at: '2025-01-11T10:30:00Z',
            status: 'active',
            version: 3,
            trust_score: 0.95,
            metadata: { lines: 1520, language: 'python', complexity: 'high' },
          },
          {
            id: 'gk-002',
            key: 'GK-2025-0111-ML-002',
            type: 'directory',
            path: 'backend/ml_intelligence',
            created_at: '2025-01-11T09:15:00Z',
            status: 'active',
            version: 5,
            trust_score: 0.88,
            metadata: { files: 12, total_lines: 4500, primary_language: 'python' },
          },
          {
            id: 'gk-003',
            key: 'GK-2025-0110-COG-001',
            type: 'file',
            path: 'backend/cognitive/ooda_loop.py',
            created_at: '2025-01-10T14:00:00Z',
            status: 'active',
            version: 2,
            trust_score: 0.91,
            metadata: { lines: 680, language: 'python', complexity: 'medium' },
          },
          {
            id: 'gk-004',
            key: 'GK-2025-0109-FE-001',
            type: 'directory',
            path: 'frontend/src/components',
            created_at: '2025-01-09T11:00:00Z',
            status: 'archived',
            version: 8,
            trust_score: 0.82,
            metadata: { files: 24, total_lines: 8200, primary_language: 'javascript' },
          },
        ]);
      }
    } catch (error) {
      console.error('Error fetching genesis keys:', error);
    }
  };

  const fetchArchives = async () => {
    try {
      const response = await fetch('/api/genesis/archives');
      if (response.ok) {
        const data = await response.json();
        setArchives(data.archives || []);
      } else {
        // Demo archives
        setArchives([
          {
            id: 'arch-001',
            date: '2025-01-10',
            keys_archived: 45,
            total_size: '12.5 MB',
            status: 'completed',
            report_available: true,
          },
          {
            id: 'arch-002',
            date: '2025-01-09',
            keys_archived: 38,
            total_size: '9.8 MB',
            status: 'completed',
            report_available: true,
          },
          {
            id: 'arch-003',
            date: '2025-01-08',
            keys_archived: 52,
            total_size: '15.2 MB',
            status: 'completed',
            report_available: true,
          },
        ]);
      }
    } catch (error) {
      console.error('Error fetching archives:', error);
    }
  };

  const fetchCurationStatus = async () => {
    try {
      const response = await fetch('/api/librarian/genesis-keys/status');
      if (response.ok) {
        const data = await response.json();
        setCurationStatus(data);
      } else {
        // Demo status
        setCurationStatus({
          scheduler_running: true,
          last_curation: '2025-01-11T06:00:00Z',
          next_scheduled: '2025-01-12T06:00:00Z',
          pending_keys: 12,
          curated_today: 23,
          backfill_needed: false,
        });
      }
    } catch (error) {
      console.error('Error fetching curation status:', error);
    }
  };

  const fetchDailySummary = async (date) => {
    try {
      const response = await fetch(`/api/librarian/genesis-keys/summary/${date}`);
      if (response.ok) {
        const data = await response.json();
        setDailySummary(data);
      } else {
        // Demo summary
        setDailySummary({
          date: date,
          total_keys: 23,
          new_keys: 8,
          updated_keys: 12,
          archived_keys: 3,
          by_type: { file: 18, directory: 5 },
          by_language: { python: 15, javascript: 6, css: 2 },
          top_paths: [
            { path: 'backend/api', count: 8 },
            { path: 'backend/ml_intelligence', count: 5 },
            { path: 'frontend/src/components', count: 4 },
          ],
        });
      }
    } catch (error) {
      console.error('Error fetching daily summary:', error);
    }
  };

  const handleCurateToday = async () => {
    try {
      const response = await fetch('/api/librarian/genesis-keys/curate-today', { method: 'POST' });
      if (response.ok) {
        fetchCurationStatus();
        fetchStats();
      }
    } catch (error) {
      console.error('Error triggering curation:', error);
    }
  };

  const handleAnalyzeCode = async (keyId) => {
    try {
      const response = await fetch('/api/genesis/analyze-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_id: keyId }),
      });
      if (response.ok) {
        const data = await response.json();
        setAnalysisResults(data);
      } else {
        // Demo analysis
        setAnalysisResults({
          key_id: keyId,
          issues: [
            { type: 'warning', message: 'Function complexity exceeds threshold', line: 145, severity: 'medium' },
            { type: 'info', message: 'Consider adding type hints', line: 89, severity: 'low' },
            { type: 'warning', message: 'Unused import detected', line: 12, severity: 'low' },
          ],
          suggestions: [
            { id: 'sug-1', description: 'Extract method for better readability', confidence: 0.85 },
            { id: 'sug-2', description: 'Add error handling for edge cases', confidence: 0.78 },
          ],
          metrics: {
            complexity: 12,
            maintainability: 0.72,
            test_coverage: 0.65,
          },
        });
      }
    } catch (error) {
      console.error('Error analyzing code:', error);
    }
  };

  const handleRollback = async (keyId) => {
    if (!window.confirm('Are you sure you want to rollback this Genesis Key?')) return;
    try {
      await fetch(`/api/genesis/keys/${keyId}/rollback`, { method: 'POST' });
      fetchGenesisKeys();
    } catch (error) {
      console.error('Error rolling back:', error);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getTrustColor = (score) => {
    if (score >= 0.9) return '#10b981';
    if (score >= 0.7) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="genesis-tab">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading Genesis Keys...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="genesis-tab">
      <div className="genesis-header">
        <div className="header-left">
          <h2>Genesis Keys</h2>
          <p>Unique identifiers tracking every file and directory in Grace</p>
        </div>
        <div className="header-stats">
          {stats && (
            <>
              <div className="stat-item">
                <span className="stat-value">{stats.total_keys}</span>
                <span className="stat-label">Total Keys</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{stats.keys_today}</span>
                <span className="stat-label">Today</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{(stats.health_score * 100).toFixed(0)}%</span>
                <span className="stat-label">Health</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="genesis-toolbar">
        <div className="view-tabs">
          <button className={view === 'dashboard' ? 'active' : ''} onClick={() => setView('dashboard')}>
            Dashboard
          </button>
          <button className={view === 'keys' ? 'active' : ''} onClick={() => setView('keys')}>
            Keys
          </button>
          <button className={view === 'archives' ? 'active' : ''} onClick={() => { setView('archives'); fetchArchives(); }}>
            Archives
          </button>
          <button className={view === 'curation' ? 'active' : ''} onClick={() => { setView('curation'); fetchCurationStatus(); fetchDailySummary('2025-01-11'); }}>
            Curation
          </button>
          <button className={view === 'analysis' ? 'active' : ''} onClick={() => setView('analysis')}>
            Analysis
          </button>
        </div>
      </div>

      <div className="genesis-content">
        {/* Dashboard View */}
        {view === 'dashboard' && stats && (
          <div className="dashboard-view">
            <div className="stats-overview">
              <div className="stat-card large">
                <span className="stat-icon">🔑</span>
                <div className="stat-info">
                  <span className="stat-value">{stats.total_keys}</span>
                  <span className="stat-label">Total Genesis Keys</span>
                </div>
              </div>
              <div className="stat-card">
                <span className="stat-icon">✓</span>
                <div className="stat-info">
                  <span className="stat-value">{stats.active_keys}</span>
                  <span className="stat-label">Active</span>
                </div>
              </div>
              <div className="stat-card">
                <span className="stat-icon">📦</span>
                <div className="stat-info">
                  <span className="stat-value">{stats.archived_keys}</span>
                  <span className="stat-label">Archived</span>
                </div>
              </div>
              <div className="stat-card">
                <span className="stat-icon">📈</span>
                <div className="stat-info">
                  <span className="stat-value">{stats.coverage_percentage}%</span>
                  <span className="stat-label">Coverage</span>
                </div>
              </div>
            </div>

            <div className="dashboard-sections">
              <div className="section recent-keys">
                <h4>Recent Genesis Keys</h4>
                <div className="key-list">
                  {genesisKeys.slice(0, 5).map((key) => (
                    <div key={key.id} className="key-item">
                      <div className="key-icon">{key.type === 'file' ? '📄' : '📁'}</div>
                      <div className="key-info">
                        <span className="key-name">{key.key}</span>
                        <span className="key-path">{key.path}</span>
                      </div>
                      <div className="key-trust" style={{ color: getTrustColor(key.trust_score) }}>
                        {(key.trust_score * 100).toFixed(0)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="section health-overview">
                <h4>System Health</h4>
                <div className="health-meter">
                  <div className="meter-fill" style={{ width: `${stats.health_score * 100}%`, background: getTrustColor(stats.health_score) }}></div>
                </div>
                <div className="health-details">
                  <div className="health-item">
                    <span>Keys This Week</span>
                    <span>{stats.keys_this_week}</span>
                  </div>
                  <div className="health-item">
                    <span>Keys Today</span>
                    <span>{stats.keys_today}</span>
                  </div>
                  <div className="health-item">
                    <span>Coverage</span>
                    <span>{stats.coverage_percentage}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Keys View */}
        {view === 'keys' && (
          <div className="keys-view">
            <div className="keys-grid">
              {genesisKeys.map((key) => (
                <div key={key.id} className={`key-card status-${key.status}`}>
                  <div className="key-card-header">
                    <span className="key-type-icon">{key.type === 'file' ? '📄' : '📁'}</span>
                    <span className="key-id">{key.key}</span>
                    <span className={`key-status status-${key.status}`}>{key.status}</span>
                  </div>
                  <div className="key-card-path">{key.path}</div>
                  <div className="key-card-meta">
                    <span>v{key.version}</span>
                    <span>{formatDate(key.created_at)}</span>
                  </div>
                  <div className="key-card-trust">
                    <span className="trust-label">Trust Score</span>
                    <div className="trust-bar">
                      <div className="trust-fill" style={{ width: `${key.trust_score * 100}%`, background: getTrustColor(key.trust_score) }}></div>
                    </div>
                    <span className="trust-value">{(key.trust_score * 100).toFixed(0)}%</span>
                  </div>
                  {key.metadata && (
                    <div className="key-card-metadata">
                      {key.metadata.lines && <span>{key.metadata.lines} lines</span>}
                      {key.metadata.files && <span>{key.metadata.files} files</span>}
                      {key.metadata.language && <span>{key.metadata.language}</span>}
                      {key.metadata.complexity && <span>{key.metadata.complexity} complexity</span>}
                    </div>
                  )}
                  <div className="key-card-actions">
                    <button className="btn-analyze" onClick={() => { handleAnalyzeCode(key.id); setView('analysis'); setSelectedKey(key); }}>
                      Analyze
                    </button>
                    <button className="btn-rollback" onClick={() => handleRollback(key.id)}>
                      Rollback
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Archives View */}
        {view === 'archives' && (
          <div className="archives-view">
            <div className="archives-header">
              <h4>Archive History</h4>
              <button className="btn-trigger-archive" onClick={() => fetch('/api/genesis/archive/trigger', { method: 'POST' })}>
                Trigger Archive
              </button>
            </div>
            <div className="archives-list">
              {archives.map((archive) => (
                <div key={archive.id} className="archive-card">
                  <div className="archive-date">
                    <span className="archive-icon">📦</span>
                    <span>{archive.date}</span>
                  </div>
                  <div className="archive-stats">
                    <span>{archive.keys_archived} keys</span>
                    <span>{archive.total_size}</span>
                    <span className={`archive-status status-${archive.status}`}>{archive.status}</span>
                  </div>
                  {archive.report_available && (
                    <button className="btn-view-report">View Report</button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Curation View */}
        {view === 'curation' && (
          <div className="curation-view">
            <div className="curation-status">
              <h4>Curation Status</h4>
              {curationStatus && (
                <div className="status-cards">
                  <div className="status-card">
                    <span className="status-indicator" style={{ background: curationStatus.scheduler_running ? '#10b981' : '#ef4444' }}></span>
                    <span>Scheduler {curationStatus.scheduler_running ? 'Running' : 'Stopped'}</span>
                  </div>
                  <div className="status-card">
                    <span>Last Curation</span>
                    <span>{formatDate(curationStatus.last_curation)}</span>
                  </div>
                  <div className="status-card">
                    <span>Next Scheduled</span>
                    <span>{formatDate(curationStatus.next_scheduled)}</span>
                  </div>
                  <div className="status-card">
                    <span>Pending Keys</span>
                    <span>{curationStatus.pending_keys}</span>
                  </div>
                </div>
              )}
              <div className="curation-actions">
                <button className="btn-curate" onClick={handleCurateToday}>Curate Today</button>
                <button className="btn-backfill" onClick={() => fetch('/api/librarian/genesis-keys/backfill', { method: 'POST' })}>
                  Backfill Missing
                </button>
              </div>
            </div>

            {dailySummary && (
              <div className="daily-summary">
                <h4>Daily Summary - {dailySummary.date}</h4>
                <div className="summary-stats">
                  <div className="summary-stat">
                    <span className="summary-value">{dailySummary.total_keys}</span>
                    <span className="summary-label">Total</span>
                  </div>
                  <div className="summary-stat">
                    <span className="summary-value">{dailySummary.new_keys}</span>
                    <span className="summary-label">New</span>
                  </div>
                  <div className="summary-stat">
                    <span className="summary-value">{dailySummary.updated_keys}</span>
                    <span className="summary-label">Updated</span>
                  </div>
                  <div className="summary-stat">
                    <span className="summary-value">{dailySummary.archived_keys}</span>
                    <span className="summary-label">Archived</span>
                  </div>
                </div>
                <div className="summary-breakdown">
                  <div className="breakdown-section">
                    <h5>By Type</h5>
                    {Object.entries(dailySummary.by_type).map(([type, count]) => (
                      <div key={type} className="breakdown-item">
                        <span>{type}</span>
                        <span>{count}</span>
                      </div>
                    ))}
                  </div>
                  <div className="breakdown-section">
                    <h5>By Language</h5>
                    {Object.entries(dailySummary.by_language).map(([lang, count]) => (
                      <div key={lang} className="breakdown-item">
                        <span>{lang}</span>
                        <span>{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Analysis View */}
        {view === 'analysis' && (
          <div className="analysis-view">
            <h4>Code Analysis {selectedKey && `- ${selectedKey.key}`}</h4>
            {!analysisResults ? (
              <div className="analysis-prompt">
                <p>Select a Genesis Key from the Keys view to analyze its code.</p>
              </div>
            ) : (
              <div className="analysis-results">
                <div className="analysis-metrics">
                  <div className="metric-card">
                    <span className="metric-value">{analysisResults.metrics.complexity}</span>
                    <span className="metric-label">Complexity</span>
                  </div>
                  <div className="metric-card">
                    <span className="metric-value">{(analysisResults.metrics.maintainability * 100).toFixed(0)}%</span>
                    <span className="metric-label">Maintainability</span>
                  </div>
                  <div className="metric-card">
                    <span className="metric-value">{(analysisResults.metrics.test_coverage * 100).toFixed(0)}%</span>
                    <span className="metric-label">Test Coverage</span>
                  </div>
                </div>

                <div className="issues-section">
                  <h5>Issues ({analysisResults.issues.length})</h5>
                  <div className="issues-list">
                    {analysisResults.issues.map((issue, idx) => (
                      <div key={idx} className={`issue-item issue-${issue.type}`}>
                        <span className="issue-type">{issue.type}</span>
                        <span className="issue-message">{issue.message}</span>
                        <span className="issue-line">Line {issue.line}</span>
                        <span className={`issue-severity severity-${issue.severity}`}>{issue.severity}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="suggestions-section">
                  <h5>Suggestions</h5>
                  <div className="suggestions-list">
                    {analysisResults.suggestions.map((sug) => (
                      <div key={sug.id} className="suggestion-item">
                        <span className="suggestion-text">{sug.description}</span>
                        <span className="suggestion-confidence">{(sug.confidence * 100).toFixed(0)}% confidence</span>
                        <button className="btn-apply">Apply Fix</button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GenesisKeyTab;
