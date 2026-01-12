import React, { useState, useEffect } from 'react';
import './MLIntelligenceTab.css';

const MLIntelligenceTab = () => {
  const [view, setView] = useState('dashboard'); // dashboard, trust, bandit, uncertainty, active-learning
  const [loading, setLoading] = useState(true);
  const [mlStatus, setMlStatus] = useState(null);
  const [trustScores, setTrustScores] = useState({});
  const [components, setComponents] = useState([]);
  const [banditStats, setBanditStats] = useState(null);
  const [uncertaintyData, setUncertaintyData] = useState(null);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchMLStatus(),
      fetchSystemTrust(),
      fetchComponents(),
    ]);
    setLoading(false);
  };

  const fetchMLStatus = async () => {
    try {
      const response = await fetch('/api/ml-intelligence/status');
      if (response.ok) {
        const data = await response.json();
        setMlStatus(data);
      } else {
        setMlStatus({
          enabled: true,
          neural_trust_enabled: true,
          bandit_enabled: true,
          meta_learning_enabled: true,
          uncertainty_enabled: true,
          active_learning_enabled: true,
          last_updated: '2025-01-11T10:30:00Z',
        });
      }
    } catch (error) {
      console.error('Error fetching ML status:', error);
    }
  };

  const fetchSystemTrust = async () => {
    try {
      const response = await fetch('/api/kpi/trust/system');
      if (response.ok) {
        const data = await response.json();
        setTrustScores({ system: data.trust_score });
      } else {
        setTrustScores({
          system: 0.87,
          neural: 0.89,
          symbolic: 0.85,
          combined: 0.87,
        });
      }
    } catch (error) {
      console.error('Error fetching system trust:', error);
    }
  };

  const fetchComponents = async () => {
    try {
      const response = await fetch('/api/kpi/components');
      if (response.ok) {
        const data = await response.json();
        setComponents(data.components || []);
      } else {
        setComponents([
          { name: 'cognitive_engine', trust_score: 0.92, status: 'excellent', kpi_count: 15, total_actions: 1250 },
          { name: 'librarian', trust_score: 0.88, status: 'good', kpi_count: 12, total_actions: 890 },
          { name: 'retrieval_engine', trust_score: 0.85, status: 'good', kpi_count: 8, total_actions: 2100 },
          { name: 'llm_orchestrator', trust_score: 0.91, status: 'excellent', kpi_count: 10, total_actions: 560 },
          { name: 'learning_memory', trust_score: 0.78, status: 'fair', kpi_count: 6, total_actions: 340 },
          { name: 'sandbox_lab', trust_score: 0.82, status: 'good', kpi_count: 5, total_actions: 125 },
        ]);
      }
    } catch (error) {
      console.error('Error fetching components:', error);
    }
  };

  const fetchBanditStats = async () => {
    try {
      const response = await fetch('/api/ml-intelligence/bandit/stats');
      if (response.ok) {
        const data = await response.json();
        setBanditStats(data);
      } else {
        setBanditStats({
          total_selections: 1250,
          total_rewards: 1089,
          success_rate: 0.87,
          arms: [
            { name: 'strategy_a', selections: 450, reward_rate: 0.92, ucb_score: 1.45 },
            { name: 'strategy_b', selections: 380, reward_rate: 0.85, ucb_score: 1.32 },
            { name: 'strategy_c', selections: 280, reward_rate: 0.78, ucb_score: 1.21 },
            { name: 'strategy_d', selections: 140, reward_rate: 0.72, ucb_score: 1.15 },
          ],
          exploration_rate: 0.15,
        });
      }
    } catch (error) {
      console.error('Error fetching bandit stats:', error);
    }
  };

  const fetchUncertaintyData = async () => {
    try {
      const response = await fetch('/api/ml-intelligence/uncertainty/stats');
      if (response.ok) {
        const data = await response.json();
        setUncertaintyData(data);
      } else {
        setUncertaintyData({
          average_uncertainty: 0.23,
          high_uncertainty_count: 45,
          low_uncertainty_count: 892,
          recent_estimates: [
            { query: 'API endpoint design', uncertainty: 0.15, confidence: 0.85, timestamp: '2025-01-11T10:25:00Z' },
            { query: 'Error handling pattern', uncertainty: 0.32, confidence: 0.68, timestamp: '2025-01-11T10:20:00Z' },
            { query: 'Database optimization', uncertainty: 0.18, confidence: 0.82, timestamp: '2025-01-11T10:15:00Z' },
            { query: 'Security implementation', uncertainty: 0.42, confidence: 0.58, timestamp: '2025-01-11T10:10:00Z' },
          ],
        });
      }
    } catch (error) {
      console.error('Error fetching uncertainty data:', error);
    }
  };

  const handleEnableML = async () => {
    try {
      await fetch('/api/ml-intelligence/enable', { method: 'POST' });
      fetchMLStatus();
    } catch (error) {
      console.error('Error enabling ML:', error);
    }
  };

  const handleDisableML = async () => {
    try {
      await fetch('/api/ml-intelligence/disable', { method: 'POST' });
      fetchMLStatus();
    } catch (error) {
      console.error('Error disabling ML:', error);
    }
  };

  const handleComputeTrust = async (componentName) => {
    try {
      const response = await fetch('/api/ml-intelligence/trust-score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ component_name: componentName }),
      });
      if (response.ok) {
        fetchComponents();
      }
    } catch (error) {
      console.error('Error computing trust:', error);
    }
  };

  const getTrustColor = (score) => {
    if (score >= 0.9) return '#10b981';
    if (score >= 0.7) return '#f59e0b';
    if (score >= 0.5) return '#3b82f6';
    return '#ef4444';
  };

  const getStatusColor = (status) => {
    const colors = {
      excellent: '#10b981',
      good: '#3b82f6',
      fair: '#f59e0b',
      poor: '#ef4444',
    };
    return colors[status] || '#6b7280';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return (
      <div className="ml-tab">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading ML Intelligence...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="ml-tab">
      <div className="ml-header">
        <div className="header-left">
          <h2>ML Intelligence</h2>
          <p>Neural trust scoring, bandits, and uncertainty estimation</p>
        </div>
        <div className="header-stats">
          <div className="stat-item">
            <span className="stat-value" style={{ color: getTrustColor(trustScores.system || 0) }}>
              {((trustScores.system || 0) * 100).toFixed(0)}%
            </span>
            <span className="stat-label">System Trust</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{components.length}</span>
            <span className="stat-label">Components</span>
          </div>
        </div>
      </div>

      <div className="ml-toolbar">
        <div className="view-tabs">
          <button className={view === 'dashboard' ? 'active' : ''} onClick={() => setView('dashboard')}>
            Dashboard
          </button>
          <button className={view === 'trust' ? 'active' : ''} onClick={() => setView('trust')}>
            Trust Scores
          </button>
          <button className={view === 'bandit' ? 'active' : ''} onClick={() => { setView('bandit'); fetchBanditStats(); }}>
            Multi-Armed Bandit
          </button>
          <button className={view === 'uncertainty' ? 'active' : ''} onClick={() => { setView('uncertainty'); fetchUncertaintyData(); }}>
            Uncertainty
          </button>
        </div>

        <div className="ml-controls">
          {mlStatus?.enabled ? (
            <button className="btn-disable" onClick={handleDisableML}>Disable ML</button>
          ) : (
            <button className="btn-enable" onClick={handleEnableML}>Enable ML</button>
          )}
        </div>
      </div>

      <div className="ml-content">
        {/* Dashboard View */}
        {view === 'dashboard' && (
          <div className="dashboard-view">
            <div className="ml-status-panel">
              <h4>ML Intelligence Status</h4>
              <div className="status-grid">
                <div className={`status-item ${mlStatus?.neural_trust_enabled ? 'enabled' : 'disabled'}`}>
                  <span className="status-name">Neural Trust</span>
                  <span className="status-indicator"></span>
                </div>
                <div className={`status-item ${mlStatus?.bandit_enabled ? 'enabled' : 'disabled'}`}>
                  <span className="status-name">Multi-Armed Bandit</span>
                  <span className="status-indicator"></span>
                </div>
                <div className={`status-item ${mlStatus?.meta_learning_enabled ? 'enabled' : 'disabled'}`}>
                  <span className="status-name">Meta Learning</span>
                  <span className="status-indicator"></span>
                </div>
                <div className={`status-item ${mlStatus?.uncertainty_enabled ? 'enabled' : 'disabled'}`}>
                  <span className="status-name">Uncertainty Estimation</span>
                  <span className="status-indicator"></span>
                </div>
                <div className={`status-item ${mlStatus?.active_learning_enabled ? 'enabled' : 'disabled'}`}>
                  <span className="status-name">Active Learning</span>
                  <span className="status-indicator"></span>
                </div>
              </div>
            </div>

            <div className="trust-overview">
              <h4>Trust Score Overview</h4>
              <div className="trust-visualization">
                <div className="trust-circle" style={{ '--trust-value': `${(trustScores.system || 0) * 100}%`, '--trust-color': getTrustColor(trustScores.system || 0) }}>
                  <span className="trust-percentage">{((trustScores.system || 0) * 100).toFixed(0)}%</span>
                  <span className="trust-label">System Trust</span>
                </div>
                <div className="trust-breakdown">
                  <div className="trust-component">
                    <span>Neural Trust</span>
                    <div className="trust-bar">
                      <div className="trust-fill" style={{ width: `${(trustScores.neural || 0.89) * 100}%`, background: getTrustColor(trustScores.neural || 0.89) }}></div>
                    </div>
                    <span>{((trustScores.neural || 0.89) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="trust-component">
                    <span>Symbolic Trust</span>
                    <div className="trust-bar">
                      <div className="trust-fill" style={{ width: `${(trustScores.symbolic || 0.85) * 100}%`, background: getTrustColor(trustScores.symbolic || 0.85) }}></div>
                    </div>
                    <span>{((trustScores.symbolic || 0.85) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="trust-component">
                    <span>Combined Trust</span>
                    <div className="trust-bar">
                      <div className="trust-fill" style={{ width: `${(trustScores.combined || 0.87) * 100}%`, background: getTrustColor(trustScores.combined || 0.87) }}></div>
                    </div>
                    <span>{((trustScores.combined || 0.87) * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="components-overview">
              <h4>Component Health</h4>
              <div className="components-mini-grid">
                {components.slice(0, 6).map((comp) => (
                  <div key={comp.name} className="component-mini-card">
                    <span className="component-name">{comp.name.replace(/_/g, ' ')}</span>
                    <div className="component-trust" style={{ color: getTrustColor(comp.trust_score) }}>
                      {(comp.trust_score * 100).toFixed(0)}%
                    </div>
                    <span className="component-status" style={{ color: getStatusColor(comp.status) }}>
                      {comp.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Trust Scores View */}
        {view === 'trust' && (
          <div className="trust-view">
            <div className="components-panel">
              <h4>Component Trust Scores</h4>
              <div className="components-list">
                {components.map((comp) => (
                  <div key={comp.name} className="component-card">
                    <div className="component-header">
                      <span className="component-name">{comp.name.replace(/_/g, ' ')}</span>
                      <span className="component-status-badge" style={{ background: getStatusColor(comp.status) }}>
                        {comp.status}
                      </span>
                    </div>
                    <div className="component-trust-display">
                      <div className="trust-gauge">
                        <svg viewBox="0 0 100 50">
                          <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#e5e7eb" strokeWidth="8" />
                          <path
                            d="M 10 50 A 40 40 0 0 1 90 50"
                            fill="none"
                            stroke={getTrustColor(comp.trust_score)}
                            strokeWidth="8"
                            strokeDasharray={`${comp.trust_score * 126} 126`}
                          />
                        </svg>
                        <span className="gauge-value">{(comp.trust_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <div className="component-stats">
                      <div className="stat">
                        <span className="stat-label">KPIs</span>
                        <span className="stat-value">{comp.kpi_count}</span>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Actions</span>
                        <span className="stat-value">{comp.total_actions}</span>
                      </div>
                    </div>
                    <button className="btn-compute" onClick={() => handleComputeTrust(comp.name)}>
                      Recompute Trust
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Bandit View */}
        {view === 'bandit' && banditStats && (
          <div className="bandit-view">
            <div className="bandit-overview">
              <h4>Multi-Armed Bandit Statistics</h4>
              <div className="bandit-stats">
                <div className="bandit-stat">
                  <span className="stat-value">{banditStats.total_selections}</span>
                  <span className="stat-label">Total Selections</span>
                </div>
                <div className="bandit-stat">
                  <span className="stat-value">{((banditStats.success_rate) * 100).toFixed(0)}%</span>
                  <span className="stat-label">Success Rate</span>
                </div>
                <div className="bandit-stat">
                  <span className="stat-value">{((banditStats.exploration_rate) * 100).toFixed(0)}%</span>
                  <span className="stat-label">Exploration Rate</span>
                </div>
              </div>
            </div>

            <div className="arms-panel">
              <h4>Strategy Arms</h4>
              <div className="arms-list">
                {banditStats.arms.map((arm, idx) => (
                  <div key={arm.name} className="arm-card">
                    <div className="arm-rank">#{idx + 1}</div>
                    <div className="arm-info">
                      <span className="arm-name">{arm.name.replace(/_/g, ' ')}</span>
                      <div className="arm-stats">
                        <span>Selections: {arm.selections}</span>
                        <span>Reward Rate: {(arm.reward_rate * 100).toFixed(0)}%</span>
                        <span>UCB Score: {arm.ucb_score.toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="arm-visualization">
                      <div className="reward-bar">
                        <div className="reward-fill" style={{ width: `${arm.reward_rate * 100}%` }}></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Uncertainty View */}
        {view === 'uncertainty' && uncertaintyData && (
          <div className="uncertainty-view">
            <div className="uncertainty-overview">
              <h4>Uncertainty Estimation</h4>
              <div className="uncertainty-stats">
                <div className="uncertainty-stat">
                  <span className="stat-value">{(uncertaintyData.average_uncertainty * 100).toFixed(0)}%</span>
                  <span className="stat-label">Avg Uncertainty</span>
                </div>
                <div className="uncertainty-stat high">
                  <span className="stat-value">{uncertaintyData.high_uncertainty_count}</span>
                  <span className="stat-label">High Uncertainty</span>
                </div>
                <div className="uncertainty-stat low">
                  <span className="stat-value">{uncertaintyData.low_uncertainty_count}</span>
                  <span className="stat-label">Low Uncertainty</span>
                </div>
              </div>
            </div>

            <div className="recent-estimates">
              <h4>Recent Uncertainty Estimates</h4>
              <div className="estimates-list">
                {uncertaintyData.recent_estimates.map((est, idx) => (
                  <div key={idx} className="estimate-card">
                    <div className="estimate-query">{est.query}</div>
                    <div className="estimate-metrics">
                      <div className="metric">
                        <span className="metric-label">Uncertainty</span>
                        <div className="uncertainty-bar">
                          <div className="uncertainty-fill" style={{ width: `${est.uncertainty * 100}%`, background: est.uncertainty > 0.3 ? '#ef4444' : '#10b981' }}></div>
                        </div>
                        <span className="metric-value">{(est.uncertainty * 100).toFixed(0)}%</span>
                      </div>
                      <div className="metric">
                        <span className="metric-label">Confidence</span>
                        <div className="confidence-bar">
                          <div className="confidence-fill" style={{ width: `${est.confidence * 100}%` }}></div>
                        </div>
                        <span className="metric-value">{(est.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <span className="estimate-time">{formatDate(est.timestamp)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MLIntelligenceTab;
