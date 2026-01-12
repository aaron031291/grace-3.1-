import React, { useState, useEffect } from 'react';
import './OrchestrationTab.css';

const OrchestrationTab = () => {
  const [view, setView] = useState('overview'); // overview, collaboration, finetune, tasks
  const [loading, setLoading] = useState(true);
  const [llmStats, setLlmStats] = useState(null);
  const [models, setModels] = useState([]);
  const [recentTasks, setRecentTasks] = useState([]);
  const [collaborations, setCollaborations] = useState([]);
  const [fineTuneJobs, setFineTuneJobs] = useState([]);

  useEffect(() => {
    fetchLLMStats();
    fetchModels();
    fetchRecentTasks();
  }, []);

  const fetchLLMStats = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/llm/stats');
      if (response.ok) {
        const data = await response.json();
        setLlmStats(data);
      } else {
        setLlmStats({
          total_tasks: 4521,
          successful_tasks: 4289,
          avg_latency: 245,
          active_models: 3,
          tokens_used_today: 125000,
        });
      }
    } catch (error) {
      console.error('Error fetching LLM stats:', error);
    }
    setLoading(false);
  };

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/llm/models');
      if (response.ok) {
        const data = await response.json();
        setModels(data.models || []);
      } else {
        setModels([
          { id: 'llama3.3', name: 'Llama 3.3 70B', status: 'ready', tasks: 2150, avg_latency: 180 },
          { id: 'qwen2.5', name: 'Qwen 2.5 32B', status: 'ready', tasks: 1890, avg_latency: 150 },
          { id: 'deepseek', name: 'DeepSeek Coder', status: 'ready', tasks: 481, avg_latency: 220 },
        ]);
      }
    } catch (error) {
      console.error('Error fetching models:', error);
    }
  };

  const fetchRecentTasks = async () => {
    try {
      const response = await fetch('/api/llm/tasks/recent');
      if (response.ok) {
        const data = await response.json();
        setRecentTasks(data.tasks || []);
      } else {
        setRecentTasks([
          { id: 't-1', type: 'query', model: 'llama3.3', status: 'completed', latency: 156, timestamp: '2025-01-11T10:28:00Z' },
          { id: 't-2', type: 'code_review', model: 'deepseek', status: 'completed', latency: 320, timestamp: '2025-01-11T10:25:00Z' },
          { id: 't-3', type: 'debate', model: 'multi-agent', status: 'running', latency: null, timestamp: '2025-01-11T10:22:00Z' },
          { id: 't-4', type: 'consensus', model: 'multi-agent', status: 'completed', latency: 890, timestamp: '2025-01-11T10:18:00Z' },
        ]);
      }
    } catch (error) {
      console.error('Error fetching tasks:', error);
    }
  };

  const fetchCollaborations = async () => {
    try {
      const response = await fetch('/api/llm/collaborate/history');
      if (response.ok) {
        const data = await response.json();
        setCollaborations(data.collaborations || []);
      } else {
        setCollaborations([
          {
            id: 'col-1',
            type: 'debate',
            topic: 'Best approach for caching strategy',
            participants: ['llama3.3', 'qwen2.5', 'deepseek'],
            status: 'completed',
            winner: 'qwen2.5',
            rounds: 3,
            timestamp: '2025-01-11T09:00:00Z',
          },
          {
            id: 'col-2',
            type: 'consensus',
            topic: 'API design patterns',
            participants: ['llama3.3', 'qwen2.5'],
            status: 'completed',
            agreement: 0.85,
            rounds: 2,
            timestamp: '2025-01-10T16:00:00Z',
          },
          {
            id: 'col-3',
            type: 'review',
            topic: 'Code review: authentication module',
            participants: ['deepseek'],
            status: 'completed',
            issues_found: 3,
            timestamp: '2025-01-10T14:00:00Z',
          },
        ]);
      }
    } catch (error) {
      console.error('Error fetching collaborations:', error);
    }
  };

  const fetchFineTuneJobs = async () => {
    try {
      const response = await fetch('/api/llm/fine-tune/jobs');
      if (response.ok) {
        const data = await response.json();
        setFineTuneJobs(data.jobs || []);
      } else {
        setFineTuneJobs([
          { id: 'ft-1', name: 'Code completion model', status: 'pending_approval', dataset_size: 5000, created: '2025-01-11T08:00:00Z' },
          { id: 'ft-2', name: 'Documentation generator', status: 'training', progress: 65, dataset_size: 3200, created: '2025-01-10T12:00:00Z' },
          { id: 'ft-3', name: 'Bug detection model', status: 'completed', dataset_size: 8500, created: '2025-01-09T10:00:00Z', metrics: { accuracy: 0.89 } },
        ]);
      }
    } catch (error) {
      console.error('Error fetching fine-tune jobs:', error);
    }
  };

  const handleDebate = async () => {
    try {
      await fetch('/api/llm/collaborate/debate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic: 'New topic' }) });
      fetchCollaborations();
    } catch (error) {
      console.error('Error starting debate:', error);
    }
  };

  const handleApproveFineTune = async (jobId) => {
    try {
      await fetch(`/api/llm/fine-tune/approve/${jobId}`, { method: 'POST' });
      fetchFineTuneJobs();
    } catch (error) {
      console.error('Error approving fine-tune:', error);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="orchestration-tab">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading LLM Orchestration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="orchestration-tab">
      <div className="orchestration-header">
        <div className="header-left">
          <h2>LLM Orchestration</h2>
          <p>Multi-agent collaboration and model management</p>
        </div>
        <div className="header-stats">
          {llmStats && (
            <>
              <div className="stat-item">
                <span className="stat-value">{llmStats.total_tasks}</span>
                <span className="stat-label">Total Tasks</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{llmStats.avg_latency}ms</span>
                <span className="stat-label">Avg Latency</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{(llmStats.tokens_used_today / 1000).toFixed(0)}k</span>
                <span className="stat-label">Tokens Today</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="orchestration-toolbar">
        <div className="view-tabs">
          <button className={view === 'overview' ? 'active' : ''} onClick={() => setView('overview')}>Overview</button>
          <button className={view === 'collaboration' ? 'active' : ''} onClick={() => { setView('collaboration'); fetchCollaborations(); }}>Collaboration</button>
          <button className={view === 'finetune' ? 'active' : ''} onClick={() => { setView('finetune'); fetchFineTuneJobs(); }}>Fine-Tuning</button>
          <button className={view === 'tasks' ? 'active' : ''} onClick={() => setView('tasks')}>Tasks</button>
        </div>
      </div>

      <div className="orchestration-content">
        {view === 'overview' && (
          <div className="overview-view">
            <div className="models-section">
              <h4>Available Models</h4>
              <div className="models-grid">
                {models.map((model) => (
                  <div key={model.id} className="model-card">
                    <div className="model-header">
                      <span className="model-name">{model.name}</span>
                      <span className={`model-status status-${model.status}`}>{model.status}</span>
                    </div>
                    <div className="model-stats">
                      <span>Tasks: {model.tasks}</span>
                      <span>Latency: {model.avg_latency}ms</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="actions-section">
              <h4>Quick Actions</h4>
              <div className="action-buttons">
                <button onClick={handleDebate}>Start Multi-Agent Debate</button>
                <button onClick={() => fetch('/api/llm/collaborate/consensus', { method: 'POST' })}>Build Consensus</button>
                <button onClick={() => fetch('/api/llm/collaborate/review', { method: 'POST' })}>Request Code Review</button>
              </div>
            </div>
          </div>
        )}

        {view === 'collaboration' && (
          <div className="collaboration-view">
            <div className="collab-header">
              <h4>Multi-Agent Collaborations</h4>
              <button className="btn-new" onClick={handleDebate}>+ New Collaboration</button>
            </div>
            <div className="collab-list">
              {collaborations.map((collab) => (
                <div key={collab.id} className={`collab-card type-${collab.type}`}>
                  <div className="collab-type">{collab.type}</div>
                  <div className="collab-info">
                    <h5>{collab.topic}</h5>
                    <div className="collab-participants">
                      {collab.participants.map((p) => <span key={p} className="participant">{p}</span>)}
                    </div>
                  </div>
                  <div className="collab-result">
                    {collab.winner && <span>Winner: {collab.winner}</span>}
                    {collab.agreement && <span>Agreement: {(collab.agreement * 100).toFixed(0)}%</span>}
                    {collab.issues_found !== undefined && <span>Issues: {collab.issues_found}</span>}
                  </div>
                  <span className="collab-rounds">{collab.rounds} rounds</span>
                  <span className="collab-time">{formatDate(collab.timestamp)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {view === 'finetune' && (
          <div className="finetune-view">
            <div className="finetune-header">
              <h4>Fine-Tuning Jobs</h4>
              <button className="btn-new" onClick={() => fetch('/api/llm/fine-tune/prepare-dataset', { method: 'POST' })}>+ Prepare Dataset</button>
            </div>
            <div className="finetune-list">
              {fineTuneJobs.map((job) => (
                <div key={job.id} className={`finetune-card status-${job.status}`}>
                  <div className="finetune-info">
                    <h5>{job.name}</h5>
                    <span className="dataset-size">{job.dataset_size} samples</span>
                  </div>
                  <span className={`finetune-status status-${job.status}`}>
                    {job.status.replace('_', ' ')}
                  </span>
                  {job.progress !== undefined && (
                    <div className="finetune-progress">
                      <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${job.progress}%` }}></div>
                      </div>
                      <span>{job.progress}%</span>
                    </div>
                  )}
                  {job.metrics && (
                    <div className="finetune-metrics">
                      <span>Accuracy: {(job.metrics.accuracy * 100).toFixed(0)}%</span>
                    </div>
                  )}
                  {job.status === 'pending_approval' && (
                    <button className="btn-approve" onClick={() => handleApproveFineTune(job.id)}>Approve</button>
                  )}
                  <span className="finetune-time">{formatDate(job.created)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {view === 'tasks' && (
          <div className="tasks-view">
            <h4>Recent LLM Tasks</h4>
            <div className="tasks-list">
              {recentTasks.map((task) => (
                <div key={task.id} className={`task-item status-${task.status}`}>
                  <span className="task-type">{task.type}</span>
                  <span className="task-model">{task.model}</span>
                  <span className={`task-status status-${task.status}`}>{task.status}</span>
                  {task.latency && <span className="task-latency">{task.latency}ms</span>}
                  <span className="task-time">{formatDate(task.timestamp)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrchestrationTab;
