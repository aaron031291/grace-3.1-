import React, { useState, useEffect } from 'react';
import './SelfHealingTab.css';

/**
 * Self-Healing Tab with OODA Integration
 * Shows Grace's autonomous healing decisions through the OODA loop
 */
const SelfHealingTab = () => {
  const [activeView, setActiveView] = useState('healing'); // healing, ooda, history, health
  const [healingDecisions, setHealingDecisions] = useState([]);
  const [selectedDecision, setSelectedDecision] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);
  const [healingHistory, setHealingHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    fetchAllData();
    startHealingStream();
    return () => setIsStreaming(false);
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchHealthStatus(),
      fetchHealingDecisions(),
      fetchHealingHistory(),
    ]);
    setLoading(false);
  };

  const fetchHealthStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/healing/health-status');
      if (response.ok) {
        const data = await response.json();
        setHealthStatus(data);
      } else {
        // Demo data
        setHealthStatus({
          overall_health: 'HEALTHY',
          health_score: 0.92,
          anomalies_detected: 2,
          active_healing: 0,
          recent_healings: 5,
          trust_level: 'MEDIUM_RISK_AUTO',
        });
      }
    } catch (error) {
      console.error('Error fetching health status:', error);
      setHealthStatus({
        overall_health: 'HEALTHY',
        health_score: 0.92,
        anomalies_detected: 0,
        active_healing: 0,
        recent_healings: 0,
        trust_level: 'MEDIUM_RISK_AUTO',
      });
    }
  };

  const fetchHealingDecisions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/healing/decisions/recent?limit=10');
      if (response.ok) {
        const data = await response.json();
        setHealingDecisions(data.decisions || []);
      } else {
        // Demo data
        setHealingDecisions([
          {
            decision_id: 'heal-001',
            anomaly_type: 'ERROR_SPIKE',
            severity: 'HIGH',
            health_before: 'DEGRADED',
            health_after: 'HEALTHY',
            healing_action: 'PROCESS_RESTART',
            trust_score: 0.75,
            status: 'completed',
            created_at: new Date().toISOString(),
            ooda_phases: {
              observe: { completed: true, data: { error_count: 15, time_window: '1 hour' } },
              orient: { completed: true, data: { strategy: 'restart_process', alternatives: 3 } },
              decide: { completed: true, data: { selected_action: 'PROCESS_RESTART', confidence: 0.75 } },
              act: { completed: true, data: { executed: true, result: 'success' } },
            },
          },
        ]);
      }
    } catch (error) {
      console.error('Error fetching healing decisions:', error);
    }
  };

  const fetchHealingHistory = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/healing/history?limit=20');
      if (response.ok) {
        const data = await response.json();
        setHealingHistory(data.history || []);
      } else {
        setHealingHistory([]);
      }
    } catch (error) {
      console.error('Error fetching healing history:', error);
    }
  };

  const startHealingStream = async () => {
    setIsStreaming(true);
    // Poll for new healing decisions every 3 seconds
    const interval = setInterval(async () => {
      try {
        const response = await fetch('http://localhost:8000/api/healing/decisions/recent?limit=10');
        if (response.ok) {
          const data = await response.json();
          setHealingDecisions(data.decisions || []);
        }
      } catch (error) {
        console.error('Error streaming healing decisions:', error);
      }
    }, 3000);

    return () => clearInterval(interval);
  };

  const fetchDecisionDetails = async (decisionId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/healing/decisions/${decisionId}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedDecision(data);
      }
    } catch (error) {
      console.error('Error fetching decision details:', error);
    }
  };

  const getHealthColor = (health) => {
    const colors = {
      HEALTHY: '#10b981',
      DEGRADED: '#f59e0b',
      WARNING: '#f59e0b',
      CRITICAL: '#ef4444',
      FAILING: '#ef4444',
    };
    return colors[health] || '#6b7280';
  };

  const getSeverityColor = (severity) => {
    const colors = {
      LOW: '#3b82f6',
      MEDIUM: '#f59e0b',
      HIGH: '#ef4444',
      CRITICAL: '#dc2626',
    };
    return colors[severity] || '#6b7280';
  };

  if (loading) {
    return (
      <div className="self-healing-tab">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading Self-Healing System...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="self-healing-tab">
      <div className="healing-header">
        <div className="header-left">
          <h2>Self-Healing System</h2>
          <p>Autonomous healing with OODA loop decision-making</p>
        </div>
        <div className="header-right">
          {isStreaming && (
            <div className="streaming-indicator">
              <span className="streaming-dot"></span>
              <span>Live Healing</span>
            </div>
          )}
          {healthStatus && (
            <div className="health-badge" style={{ background: getHealthColor(healthStatus.overall_health) }}>
              <span>{healthStatus.overall_health}</span>
              <span>{(healthStatus.health_score * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="healing-nav">
        <button
          className={`nav-button ${activeView === 'healing' ? 'active' : ''}`}
          onClick={() => setActiveView('healing')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14.121 1.879a3 3 0 0 0-4.242 0L8.733 3.026l4.261 4.26 1.127-1.165a3 3 0 0 0 0-4.242M12.293 8 8.027 3.734 3.738 8.031 8 12.293zm-5.006 4.994L3.03 8.737 1.879 9.88a3 3 0 0 0 4.241 4.24l.006-.006 1.16-1.121Z" />
          </svg>
          Active Healing
        </button>
        <button
          className={`nav-button ${activeView === 'ooda' ? 'active' : ''}`}
          onClick={() => setActiveView('ooda')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6m5-9l-4 4m-2 2l-4 4m10-12l-4 4m-2 2l-4 4M1 12h6m6 0h6"></path>
          </svg>
          OODA Loop
        </button>
        <button
          className={`nav-button ${activeView === 'history' ? 'active' : ''}`}
          onClick={() => setActiveView('history')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 3v18h18"></path>
            <path d="M18 7v4M12 5v10M6 9v6"></path>
          </svg>
          History
        </button>
        <button
          className={`nav-button ${activeView === 'health' ? 'active' : ''}`}
          onClick={() => setActiveView('health')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="12 3 20 7.5 20 16.5 12 21 4 16.5 4 7.5 12 3"></polyline>
            <line x1="12" y1="12" x2="20" y2="7.5"></line>
            <line x1="12" y1="12" x2="12" y2="21"></line>
            <line x1="12" y1="12" x2="4" y2="7.5"></line>
          </svg>
          System Health
        </button>
      </div>

      {/* Active Healing View */}
      {activeView === 'healing' && (
        <div className="healing-view">
          <div className="healing-timeline">
            {healingDecisions.length === 0 ? (
              <div className="empty-state">
                <p>No active healing decisions. System is healthy.</p>
              </div>
            ) : (
              healingDecisions.map((decision) => (
                <div
                  key={decision.decision_id}
                  className={`healing-decision ${decision.status}`}
                  onClick={() => {
                    fetchDecisionDetails(decision.decision_id);
                    setActiveView('ooda');
                  }}
                >
                  <div className="decision-header">
                    <span className="decision-id">{decision.decision_id}</span>
                    <span className={`severity-badge ${decision.severity?.toLowerCase()}`} style={{ background: getSeverityColor(decision.severity) }}>
                      {decision.severity}
                    </span>
                    <span className={`status-badge ${decision.status}`}>
                      {decision.status}
                    </span>
                  </div>
                  <div className="decision-content">
                    <div className="anomaly-info">
                      <strong>Anomaly:</strong> {decision.anomaly_type}
                    </div>
                    <div className="health-change">
                      <span className="health-before">{decision.health_before}</span>
                      <span>→</span>
                      <span className="health-after">{decision.health_after}</span>
                    </div>
                    <div className="healing-action">
                      <strong>Action:</strong> {decision.healing_action}
                    </div>
                    <div className="trust-score">
                      Trust: <strong>{(decision.trust_score * 100).toFixed(0)}%</strong>
                    </div>
                  </div>
                  <div className="decision-time">
                    {new Date(decision.created_at).toLocaleString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* OODA Loop View */}
      {activeView === 'ooda' && (
        <div className="ooda-view">
          {selectedDecision ? (
            <div className="ooda-breakdown">
              <div className="ooda-header">
                <h3>Healing Decision: {selectedDecision.decision_id}</h3>
                <span className={`status-badge ${selectedDecision.status}`}>
                  {selectedDecision.status}
                </span>
              </div>

              <div className="ooda-phases">
                {/* Observe Phase */}
                <div className="phase-card">
                  <div className="phase-header">
                    <div className="phase-number">1</div>
                    <h4>Observe</h4>
                    <span className={`phase-status ${selectedDecision.ooda_phases?.observe?.completed ? 'complete' : 'pending'}`}>
                      {selectedDecision.ooda_phases?.observe?.completed ? '✓' : '○'}
                    </span>
                  </div>
                  <div className="phase-content">
                    {selectedDecision.ooda_phases?.observe?.data && (
                      <div className="phase-data">
                        {Object.entries(selectedDecision.ooda_phases.observe.data).map(([key, value]) => (
                          <div key={key} className="data-item">
                            <strong>{key}:</strong> {JSON.stringify(value)}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Orient Phase */}
                <div className="phase-card">
                  <div className="phase-header">
                    <div className="phase-number">2</div>
                    <h4>Orient</h4>
                    <span className={`phase-status ${selectedDecision.ooda_phases?.orient?.completed ? 'complete' : 'pending'}`}>
                      {selectedDecision.ooda_phases?.orient?.completed ? '✓' : '○'}
                    </span>
                  </div>
                  <div className="phase-content">
                    {selectedDecision.ooda_phases?.orient?.data && (
                      <div className="phase-data">
                        {Object.entries(selectedDecision.ooda_phases.orient.data).map(([key, value]) => (
                          <div key={key} className="data-item">
                            <strong>{key}:</strong> {JSON.stringify(value)}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Decide Phase */}
                <div className="phase-card">
                  <div className="phase-header">
                    <div className="phase-number">3</div>
                    <h4>Decide</h4>
                    <span className={`phase-status ${selectedDecision.ooda_phases?.decide?.completed ? 'complete' : 'pending'}`}>
                      {selectedDecision.ooda_phases?.decide?.completed ? '✓' : '○'}
                    </span>
                  </div>
                  <div className="phase-content">
                    {selectedDecision.ooda_phases?.decide?.data && (
                      <div className="phase-data">
                        <div className="selected-action">
                          <strong>Selected Action:</strong> {selectedDecision.ooda_phases.decide.data.selected_action}
                        </div>
                        <div className="confidence">
                          <strong>Confidence:</strong> {(selectedDecision.ooda_phases.decide.data.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Act Phase */}
                <div className="phase-card">
                  <div className="phase-header">
                    <div className="phase-number">4</div>
                    <h4>Act</h4>
                    <span className={`phase-status ${selectedDecision.ooda_phases?.act?.completed ? 'complete' : 'pending'}`}>
                      {selectedDecision.ooda_phases?.act?.completed ? '✓' : '○'}
                    </span>
                  </div>
                  <div className="phase-content">
                    {selectedDecision.ooda_phases?.act?.data && (
                      <div className="phase-data">
                        <div className="execution-result">
                          <strong>Executed:</strong> {selectedDecision.ooda_phases.act.data.executed ? 'Yes' : 'No'}
                        </div>
                        <div className="result">
                          <strong>Result:</strong> {selectedDecision.ooda_phases.act.data.result}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>Select a healing decision from Active Healing to view OODA breakdown</p>
            </div>
          )}
        </div>
      )}

      {/* History View */}
      {activeView === 'history' && (
        <div className="history-view">
          <div className="history-list">
            {healingHistory.length === 0 ? (
              <div className="empty-state">
                <p>No healing history available</p>
              </div>
            ) : (
              healingHistory.map((item) => (
                <div key={item.id} className="history-item">
                  <div className="history-header">
                    <span className="history-date">{new Date(item.timestamp).toLocaleString()}</span>
                    <span className={`history-status ${item.status}`}>{item.status}</span>
                  </div>
                  <div className="history-content">
                    <div><strong>Action:</strong> {item.action}</div>
                    <div><strong>Anomaly:</strong> {item.anomaly_type}</div>
                    <div><strong>Result:</strong> {item.result}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* System Health View */}
      {activeView === 'health' && healthStatus && (
        <div className="health-view">
          <div className="health-overview">
            <div className="health-card">
              <h4>Overall Health</h4>
              <div className="health-meter">
                <div
                  className="meter-fill"
                  style={{
                    width: `${healthStatus.health_score * 100}%`,
                    background: getHealthColor(healthStatus.overall_health),
                  }}
                ></div>
              </div>
              <div className="health-value">{(healthStatus.health_score * 100).toFixed(0)}%</div>
            </div>

            <div className="health-stats">
              <div className="stat-card">
                <span className="stat-value">{healthStatus.anomalies_detected}</span>
                <span className="stat-label">Anomalies Detected</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{healthStatus.active_healing}</span>
                <span className="stat-label">Active Healing</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{healthStatus.recent_healings}</span>
                <span className="stat-label">Recent Healings</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{healthStatus.trust_level}</span>
                <span className="stat-label">Trust Level</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SelfHealingTab;
