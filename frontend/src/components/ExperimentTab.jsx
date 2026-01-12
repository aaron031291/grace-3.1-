import React, { useState, useEffect } from 'react';
import './ExperimentTab.css';

const ExperimentTab = () => {
  const [view, setView] = useState('active'); // active, pending, completed, propose
  const [loading, setLoading] = useState(true);
  const [experiments, setExperiments] = useState([]);
  const [labStatus, setLabStatus] = useState(null);
  const [selectedExperiment, setSelectedExperiment] = useState(null);
  const [showProposeModal, setShowProposeModal] = useState(false);
  const [newExperiment, setNewExperiment] = useState({ name: '', hypothesis: '', methodology: '', metrics: '' });

  useEffect(() => {
    fetchLabStatus();
    fetchExperiments();
  }, []);

  const fetchLabStatus = async () => {
    try {
      const response = await fetch('/api/sandbox-lab/status');
      if (response.ok) {
        const data = await response.json();
        setLabStatus(data);
      } else {
        setLabStatus({
          active_experiments: 3,
          pending_approval: 5,
          completed_today: 8,
          success_rate: 0.78,
          continuous_testing: true,
        });
      }
    } catch (error) {
      console.error('Error fetching lab status:', error);
    }
  };

  const fetchExperiments = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/sandbox-lab/experiments');
      if (response.ok) {
        const data = await response.json();
        setExperiments(data.experiments || []);
      } else {
        setExperiments([
          {
            id: 'exp-1',
            name: 'Improved Retrieval Algorithm',
            hypothesis: 'Using hybrid search will improve retrieval accuracy by 15%',
            status: 'running',
            phase: 'trial',
            progress: 65,
            trials: { completed: 13, total: 20 },
            metrics: { accuracy: 0.82, latency: 45 },
            created: '2025-01-11T08:00:00Z',
          },
          {
            id: 'exp-2',
            name: 'Trust Score Optimization',
            hypothesis: 'Adjusting decay rate will improve trust calibration',
            status: 'running',
            phase: 'implementation',
            progress: 30,
            trials: { completed: 0, total: 15 },
            metrics: {},
            created: '2025-01-11T09:30:00Z',
          },
          {
            id: 'exp-3',
            name: 'API Response Caching',
            hypothesis: 'Caching frequent queries will reduce latency by 40%',
            status: 'pending',
            phase: 'proposal',
            progress: 0,
            trials: { completed: 0, total: 10 },
            metrics: {},
            created: '2025-01-11T10:00:00Z',
          },
          {
            id: 'exp-4',
            name: 'Neural Embedding Update',
            hypothesis: 'New embedding model will improve semantic search',
            status: 'completed',
            phase: 'analysis',
            progress: 100,
            trials: { completed: 25, total: 25 },
            metrics: { accuracy: 0.91, improvement: 0.12 },
            created: '2025-01-10T14:00:00Z',
            result: 'success',
          },
        ]);
      }
    } catch (error) {
      console.error('Error fetching experiments:', error);
    }
    setLoading(false);
  };

  const handleProposeExperiment = async () => {
    try {
      await fetch('/api/sandbox-lab/experiments/propose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newExperiment),
      });
      setShowProposeModal(false);
      setNewExperiment({ name: '', hypothesis: '', methodology: '', metrics: '' });
      fetchExperiments();
    } catch (error) {
      console.error('Error proposing experiment:', error);
    }
  };

  const handleApprove = async (expId) => {
    try {
      await fetch(`/api/sandbox-lab/experiments/${expId}/approve`, { method: 'POST' });
      fetchExperiments();
    } catch (error) {
      console.error('Error approving experiment:', error);
    }
  };

  const handleReject = async (expId) => {
    try {
      await fetch(`/api/sandbox-lab/experiments/${expId}/reject`, { method: 'POST' });
      fetchExperiments();
    } catch (error) {
      console.error('Error rejecting experiment:', error);
    }
  };

  const getFilteredExperiments = () => {
    switch (view) {
      case 'active':
        return experiments.filter(e => e.status === 'running');
      case 'pending':
        return experiments.filter(e => e.status === 'pending');
      case 'completed':
        return experiments.filter(e => e.status === 'completed');
      default:
        return experiments;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return (
      <div className="experiment-tab">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading experiments...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="experiment-tab">
      <div className="experiment-header">
        <div className="header-left">
          <h2>Experiment Lab</h2>
          <p>Sandbox testing and continuous improvement</p>
        </div>
        <div className="header-stats">
          {labStatus && (
            <>
              <div className="stat-item">
                <span className="stat-value">{labStatus.active_experiments}</span>
                <span className="stat-label">Active</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{labStatus.pending_approval}</span>
                <span className="stat-label">Pending</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{(labStatus.success_rate * 100).toFixed(0)}%</span>
                <span className="stat-label">Success Rate</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="experiment-toolbar">
        <div className="view-tabs">
          <button className={view === 'active' ? 'active' : ''} onClick={() => setView('active')}>
            Active
          </button>
          <button className={view === 'pending' ? 'active' : ''} onClick={() => setView('pending')}>
            Pending Approval
          </button>
          <button className={view === 'completed' ? 'active' : ''} onClick={() => setView('completed')}>
            Completed
          </button>
        </div>
        <button className="btn-propose" onClick={() => setShowProposeModal(true)}>
          + Propose Experiment
        </button>
      </div>

      <div className="experiment-content">
        <div className="experiments-grid">
          {getFilteredExperiments().map((exp) => (
            <div key={exp.id} className={`experiment-card status-${exp.status}`}>
              <div className="exp-header">
                <h4>{exp.name}</h4>
                <span className={`exp-status status-${exp.status}`}>{exp.status}</span>
              </div>
              <p className="exp-hypothesis">{exp.hypothesis}</p>
              <div className="exp-phase">
                <span className="phase-label">Phase:</span>
                <span className={`phase-badge phase-${exp.phase}`}>{exp.phase}</span>
              </div>
              {exp.status === 'running' && (
                <div className="exp-progress">
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${exp.progress}%` }}></div>
                  </div>
                  <span className="progress-text">{exp.progress}%</span>
                </div>
              )}
              {exp.trials && (
                <div className="exp-trials">
                  <span>Trials: {exp.trials.completed}/{exp.trials.total}</span>
                </div>
              )}
              {Object.keys(exp.metrics).length > 0 && (
                <div className="exp-metrics">
                  {exp.metrics.accuracy && <span>Accuracy: {(exp.metrics.accuracy * 100).toFixed(0)}%</span>}
                  {exp.metrics.latency && <span>Latency: {exp.metrics.latency}ms</span>}
                  {exp.metrics.improvement && <span>Improvement: +{(exp.metrics.improvement * 100).toFixed(0)}%</span>}
                </div>
              )}
              <div className="exp-footer">
                <span className="exp-date">{formatDate(exp.created)}</span>
                {exp.status === 'pending' && (
                  <div className="exp-actions">
                    <button className="btn-approve" onClick={() => handleApprove(exp.id)}>Approve</button>
                    <button className="btn-reject" onClick={() => handleReject(exp.id)}>Reject</button>
                  </div>
                )}
                {exp.result && (
                  <span className={`exp-result result-${exp.result}`}>{exp.result}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Propose Modal */}
      {showProposeModal && (
        <div className="modal-overlay" onClick={() => setShowProposeModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Propose New Experiment</h3>
              <button className="modal-close" onClick={() => setShowProposeModal(false)}>×</button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); handleProposeExperiment(); }}>
              <div className="form-group">
                <label>Experiment Name</label>
                <input
                  type="text"
                  value={newExperiment.name}
                  onChange={(e) => setNewExperiment({ ...newExperiment, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Hypothesis</label>
                <textarea
                  value={newExperiment.hypothesis}
                  onChange={(e) => setNewExperiment({ ...newExperiment, hypothesis: e.target.value })}
                  rows={3}
                  required
                />
              </div>
              <div className="form-group">
                <label>Methodology</label>
                <textarea
                  value={newExperiment.methodology}
                  onChange={(e) => setNewExperiment({ ...newExperiment, methodology: e.target.value })}
                  rows={3}
                />
              </div>
              <div className="form-group">
                <label>Success Metrics</label>
                <input
                  type="text"
                  value={newExperiment.metrics}
                  onChange={(e) => setNewExperiment({ ...newExperiment, metrics: e.target.value })}
                  placeholder="e.g., accuracy > 85%, latency < 50ms"
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowProposeModal(false)}>Cancel</button>
                <button type="submit" className="btn-submit">Propose</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExperimentTab;
