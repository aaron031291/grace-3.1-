import React, { useState, useEffect } from 'react';
import './LearningTab.css';

const LearningTab = () => {
  const [view, setView] = useState('dashboard'); // dashboard, autonomous, proactive, training, memory
  const [loading, setLoading] = useState(true);
  const [autonomousStatus, setAutonomousStatus] = useState(null);
  const [proactiveStatus, setProactiveStatus] = useState(null);
  const [taskQueue, setTaskQueue] = useState([]);
  const [skills, setSkills] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [memoryStats, setMemoryStats] = useState(null);
  const [trainingData, setTrainingData] = useState([]);
  const [studyTopic, setStudyTopic] = useState('API design best practices');
  const [practiceSkillName, setPracticeSkillName] = useState('Code refactoring patterns');
  const [practiceTaskDescription, setPracticeTaskDescription] = useState('Refactor a function to improve readability and add error handling');
  const [trainingActionStatus, setTrainingActionStatus] = useState(null);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchAutonomousStatus(),
      fetchProactiveStatus(),
      fetchSkills(),
      fetchAnalytics(),
      fetchMemoryStats(),
    ]);
    setLoading(false);
  };

  const fetchAutonomousStatus = async () => {
    try {
      const response = await fetch('/autonomous-learning/status');
      if (response.ok) {
        const data = await response.json();
        setAutonomousStatus(data);
      } else {
        setAutonomousStatus({
          running: true,
          started_at: '2025-01-11T08:00:00Z',
          tasks_completed: 156,
          current_task: 'Analyzing API patterns',
          learning_rate: 0.85,
          efficiency: 0.92,
        });
      }
    } catch (error) {
      console.error('Error fetching autonomous status:', error);
    }
  };

  const fetchProactiveStatus = async () => {
    try {
      const response = await fetch('/proactive-learning/status');
      if (response.ok) {
        const data = await response.json();
        setProactiveStatus(data);
      } else {
        setProactiveStatus({
          running: true,
          queue_size: 12,
          processed_today: 45,
          velocity: 8.5,
          subagent_count: 3,
        });
      }
    } catch (error) {
      console.error('Error fetching proactive status:', error);
    }
  };

  const fetchTaskQueue = async () => {
    try {
      const response = await fetch('/proactive-learning/tasks/queue');
      if (response.ok) {
        const data = await response.json();
        setTaskQueue(data.tasks || []);
      } else {
        setTaskQueue([
          { id: 'task-1', type: 'study', topic: 'Neural network optimization', priority: 'high', status: 'in_progress', progress: 65 },
          { id: 'task-2', type: 'practice', topic: 'Code refactoring patterns', priority: 'medium', status: 'queued', progress: 0 },
          { id: 'task-3', type: 'study', topic: 'API design best practices', priority: 'medium', status: 'queued', progress: 0 },
          { id: 'task-4', type: 'practice', topic: 'Error handling strategies', priority: 'low', status: 'queued', progress: 0 },
        ]);
      }
    } catch (error) {
      console.error('Error fetching task queue:', error);
    }
  };

  const fetchSkills = async () => {
    try {
      const response = await fetch('/training/skills');
      if (response.ok) {
        const data = await response.json();
        setSkills(data.skills || []);
      } else {
        setSkills([
          { name: 'Python Programming', level: 92, experience: 1250, trend: 'up' },
          { name: 'API Design', level: 85, experience: 890, trend: 'up' },
          { name: 'Code Analysis', level: 88, experience: 1100, trend: 'stable' },
          { name: 'Documentation', level: 78, experience: 650, trend: 'up' },
          { name: 'Testing', level: 72, experience: 480, trend: 'up' },
          { name: 'Refactoring', level: 81, experience: 720, trend: 'stable' },
        ]);
      }
    } catch (error) {
      console.error('Error fetching skills:', error);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await fetch('/training/analytics/progress');
      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      } else {
        setAnalytics({
          total_learning_hours: 342,
          tasks_completed_week: 89,
          improvement_rate: 12.5,
          focus_areas: ['API patterns', 'Error handling', 'Performance optimization'],
          weekly_progress: [
            { day: 'Mon', hours: 4.2, tasks: 12 },
            { day: 'Tue', hours: 5.1, tasks: 15 },
            { day: 'Wed', hours: 3.8, tasks: 11 },
            { day: 'Thu', hours: 4.5, tasks: 13 },
            { day: 'Fri', hours: 4.0, tasks: 12 },
            { day: 'Sat', hours: 2.5, tasks: 8 },
            { day: 'Sun', hours: 2.0, tasks: 6 },
          ],
        });
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  const fetchMemoryStats = async () => {
    try {
      const response = await fetch('/learning-memory/stats');
      if (response.ok) {
        const data = await response.json();
        setMemoryStats(data);
      } else {
        setMemoryStats({
          total_experiences: 4521,
          positive_feedback: 3890,
          negative_feedback: 245,
          neutral_feedback: 386,
          trust_decay_rate: 0.02,
          last_snapshot: '2025-01-11T06:00:00Z',
          snapshots_count: 45,
        });
      }
    } catch (error) {
      console.error('Error fetching memory stats:', error);
    }
  };

  const handleStartAutonomous = async () => {
    try {
      await fetch('/autonomous-learning/start', { method: 'POST' });
      fetchAutonomousStatus();
    } catch (error) {
      console.error('Error starting autonomous learning:', error);
    }
  };

  const handleStopAutonomous = async () => {
    try {
      await fetch('/autonomous-learning/stop', { method: 'POST' });
      fetchAutonomousStatus();
    } catch (error) {
      console.error('Error stopping autonomous learning:', error);
    }
  };

  const handleStartProactive = async () => {
    try {
      await fetch('/proactive-learning/start', { method: 'POST' });
      fetchProactiveStatus();
    } catch (error) {
      console.error('Error starting proactive learning:', error);
    }
  };

  const handleStopProactive = async () => {
    try {
      await fetch('/proactive-learning/stop', { method: 'POST' });
      fetchProactiveStatus();
    } catch (error) {
      console.error('Error stopping proactive learning:', error);
    }
  };

  const handleAddTask = async (type, topic) => {
    try {
      await fetch('/proactive-learning/tasks/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, topic }),
      });
      fetchTaskQueue();
    } catch (error) {
      console.error('Error adding task:', error);
    }
  };

  const handleCreateSnapshot = async () => {
    try {
      await fetch('/learning-memory/snapshot/create', { method: 'POST' });
      fetchMemoryStats();
    } catch (error) {
      console.error('Error creating snapshot:', error);
    }
  };

  const handleSubmitStudyTask = async () => {
    setTrainingActionStatus(null);
    try {
      const response = await fetch('/autonomous-learning/tasks/study', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: studyTopic,
          learning_objectives: [],
          priority: 5,
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.detail || `Request failed (${response.status})`);
      }
      
      // Show success with task ID and queue info
      const queueInfo = data.queue_size ? ` (${data.queue_size} tasks in queue)` : '';
      setTrainingActionStatus({ 
        type: 'success', 
        message: `✓ ${data.message || 'Study task queued'}${queueInfo}\nTask ID: ${data.task_id}` 
      });
      
      // Refresh status after a short delay
      setTimeout(() => {
        fetchAutonomousStatus();
      }, 1000);
    } catch (error) {
      console.error('Error submitting study task:', error);
      setTrainingActionStatus({ type: 'error', message: `✗ Study task failed: ${error.message}` });
    }
  };

  const handleSubmitPracticeTask = async () => {
    setTrainingActionStatus(null);
    try {
      const response = await fetch('/autonomous-learning/tasks/practice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_name: practiceSkillName,
          task_description: practiceTaskDescription,
          complexity: 0.5,
          priority: 5,
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.detail || `Request failed (${response.status})`);
      }
      
      // Show success with task ID and queue info
      const queueInfo = data.queue_size ? ` (${data.queue_size} tasks in queue)` : '';
      setTrainingActionStatus({ 
        type: 'success', 
        message: `✓ ${data.message || 'Practice task queued'}${queueInfo}\nTask ID: ${data.task_id}` 
      });
      
      // Refresh status after a short delay
      setTimeout(() => {
        fetchAutonomousStatus();
      }, 1000);
    } catch (error) {
      console.error('Error submitting practice task:', error);
      setTrainingActionStatus({ type: 'error', message: `✗ Practice task failed: ${error.message}` });
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getSkillColor = (level) => {
    if (level >= 90) return '#10b981';
    if (level >= 75) return '#3b82f6';
    if (level >= 60) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="learning-tab">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading learning systems...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="learning-tab">
      <div className="learning-header">
        <div className="header-left">
          <h2>Learning Center</h2>
          <p>Autonomous and proactive learning systems</p>
        </div>
        <div className="header-stats">
          {analytics && (
            <>
              <div className="stat-item">
                <span className="stat-value">{analytics.total_learning_hours}h</span>
                <span className="stat-label">Total Hours</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{analytics.tasks_completed_week}</span>
                <span className="stat-label">Tasks/Week</span>
              </div>
              <div className="stat-item positive">
                <span className="stat-value">+{analytics.improvement_rate}%</span>
                <span className="stat-label">Improvement</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="learning-toolbar">
        <div className="view-tabs">
          <button className={view === 'dashboard' ? 'active' : ''} onClick={() => setView('dashboard')}>
            Dashboard
          </button>
          <button className={view === 'autonomous' ? 'active' : ''} onClick={() => setView('autonomous')}>
            Autonomous
          </button>
          <button className={view === 'proactive' ? 'active' : ''} onClick={() => { setView('proactive'); fetchTaskQueue(); }}>
            Proactive
          </button>
          <button className={view === 'training' ? 'active' : ''} onClick={() => setView('training')}>
            Training
          </button>
          <button className={view === 'memory' ? 'active' : ''} onClick={() => setView('memory')}>
            Memory
          </button>
        </div>

        <div className="system-status">
          <span className={`status-badge ${autonomousStatus?.running ? 'running' : 'stopped'}`}>
            Autonomous: {autonomousStatus?.running ? 'Running' : 'Stopped'}
          </span>
          <span className={`status-badge ${proactiveStatus?.running ? 'running' : 'stopped'}`}>
            Proactive: {proactiveStatus?.running ? 'Running' : 'Stopped'}
          </span>
        </div>
      </div>

      <div className="learning-content">
        {/* Dashboard View */}
        {view === 'dashboard' && (
          <div className="dashboard-view">
            <div className="dashboard-grid">
              <div className="panel system-overview">
                <h4>System Overview</h4>
                <div className="overview-cards">
                  <div className="overview-card">
                    <div className="overview-icon">🤖</div>
                    <div className="overview-info">
                      <span className="overview-title">Autonomous Learning</span>
                      <span className={`overview-status ${autonomousStatus?.running ? 'active' : 'inactive'}`}>
                        {autonomousStatus?.running ? 'Active' : 'Inactive'}
                      </span>
                      {autonomousStatus?.current_task && (
                        <span className="overview-task">{autonomousStatus.current_task}</span>
                      )}
                    </div>
                    <button
                      className={`btn-toggle ${autonomousStatus?.running ? 'stop' : 'start'}`}
                      onClick={autonomousStatus?.running ? handleStopAutonomous : handleStartAutonomous}
                    >
                      {autonomousStatus?.running ? 'Stop' : 'Start'}
                    </button>
                  </div>
                  <div className="overview-card">
                    <div className="overview-icon">🎯</div>
                    <div className="overview-info">
                      <span className="overview-title">Proactive Learning</span>
                      <span className={`overview-status ${proactiveStatus?.running ? 'active' : 'inactive'}`}>
                        {proactiveStatus?.running ? 'Active' : 'Inactive'}
                      </span>
                      <span className="overview-queue">{proactiveStatus?.queue_size || 0} tasks in queue</span>
                    </div>
                    <button
                      className={`btn-toggle ${proactiveStatus?.running ? 'stop' : 'start'}`}
                      onClick={proactiveStatus?.running ? handleStopProactive : handleStartProactive}
                    >
                      {proactiveStatus?.running ? 'Stop' : 'Start'}
                    </button>
                  </div>
                </div>
              </div>

              <div className="panel skills-overview">
                <h4>Top Skills</h4>
                <div className="skills-mini-list">
                  {skills.slice(0, 4).map((skill) => (
                    <div key={skill.name} className="skill-mini">
                      <span className="skill-name">{skill.name}</span>
                      <div className="skill-bar">
                        <div className="skill-fill" style={{ width: `${skill.level}%`, background: getSkillColor(skill.level) }}></div>
                      </div>
                      <span className="skill-level">{skill.level}%</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel weekly-activity">
                <h4>Weekly Activity</h4>
                {analytics && (
                  <div className="activity-chart">
                    {(analytics.weekly_progress || []).map((day) => (
                      <div key={day.day} className="activity-bar-container">
                        <div className="activity-bar" style={{ height: `${(day.hours / 6) * 100}%` }}>
                          <span className="activity-value">{day.tasks}</span>
                        </div>
                        <span className="activity-label">{day.day}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="panel focus-areas">
                <h4>Current Focus Areas</h4>
                {analytics && (
                  <div className="focus-list">
                    {(analytics.focus_areas || []).map((area, idx) => (
                      <div key={idx} className="focus-item">
                        <span className="focus-icon">📚</span>
                        <span className="focus-name">{area}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Autonomous View */}
        {view === 'autonomous' && (
          <div className="autonomous-view">
            <div className="autonomous-status-panel">
              <div className="status-header">
                <h4>Autonomous Learning Status</h4>
                <button
                  className={`btn-control ${autonomousStatus?.running ? 'stop' : 'start'}`}
                  onClick={autonomousStatus?.running ? handleStopAutonomous : handleStartAutonomous}
                >
                  {autonomousStatus?.running ? 'Stop Learning' : 'Start Learning'}
                </button>
              </div>
              {autonomousStatus && (
                <div className="status-details">
                  <div className="status-row">
                    <span className="status-label">Status</span>
                    <span className={`status-value ${autonomousStatus.running ? 'active' : 'inactive'}`}>
                      {autonomousStatus.running ? 'Running' : 'Stopped'}
                    </span>
                  </div>
                  {autonomousStatus.started_at && (
                    <div className="status-row">
                      <span className="status-label">Started At</span>
                      <span className="status-value">{formatDate(autonomousStatus.started_at)}</span>
                    </div>
                  )}
                  <div className="status-row">
                    <span className="status-label">Tasks Completed</span>
                    <span className="status-value">{autonomousStatus.tasks_completed}</span>
                  </div>
                  {autonomousStatus.current_task && (
                    <div className="status-row">
                      <span className="status-label">Current Task</span>
                      <span className="status-value">{autonomousStatus.current_task}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="metrics-panel">
              <h4>Learning Metrics</h4>
              <div className="metrics-grid">
                <div className="metric-card">
                  <span className="metric-value">{((autonomousStatus?.learning_rate || 0) * 100).toFixed(0)}%</span>
                  <span className="metric-label">Learning Rate</span>
                </div>
                <div className="metric-card">
                  <span className="metric-value">{((autonomousStatus?.efficiency || 0) * 100).toFixed(0)}%</span>
                  <span className="metric-label">Efficiency</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Proactive View */}
        {view === 'proactive' && (
          <div className="proactive-view">
            <div className="proactive-status-panel">
              <div className="status-header">
                <h4>Proactive Learning Status</h4>
                <button
                  className={`btn-control ${proactiveStatus?.running ? 'stop' : 'start'}`}
                  onClick={proactiveStatus?.running ? handleStopProactive : handleStartProactive}
                >
                  {proactiveStatus?.running ? 'Stop Learning' : 'Start Learning'}
                </button>
              </div>
              {proactiveStatus && (
                <div className="proactive-metrics">
                  <div className="metric-item">
                    <span className="metric-value">{proactiveStatus.queue_size}</span>
                    <span className="metric-label">Queue Size</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-value">{proactiveStatus.processed_today}</span>
                    <span className="metric-label">Processed Today</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-value">{proactiveStatus.velocity}/hr</span>
                    <span className="metric-label">Velocity</span>
                  </div>
                  <div className="metric-item">
                    <span className="metric-value">{proactiveStatus.subagent_count}</span>
                    <span className="metric-label">Subagents</span>
                  </div>
                </div>
              )}
            </div>

            <div className="task-queue-panel">
              <div className="queue-header">
                <h4>Task Queue</h4>
                <div className="queue-actions">
                  <button className="btn-add-task" onClick={() => handleAddTask('study', 'New topic')}>
                    + Add Study Task
                  </button>
                  <button className="btn-add-task" onClick={() => handleAddTask('practice', 'New practice')}>
                    + Add Practice Task
                  </button>
                </div>
              </div>
              <div className="task-list">
                {taskQueue.map((task) => (
                  <div key={task.id} className={`task-item status-${task.status}`}>
                    <div className="task-type-badge">{task.type}</div>
                    <div className="task-info">
                      <span className="task-topic">{task.topic}</span>
                      <span className={`task-priority priority-${task.priority}`}>{task.priority}</span>
                    </div>
                    {task.status === 'in_progress' && (
                      <div className="task-progress">
                        <div className="progress-bar">
                          <div className="progress-fill" style={{ width: `${task.progress}%` }}></div>
                        </div>
                        <span className="progress-text">{task.progress}%</span>
                      </div>
                    )}
                    <span className={`task-status status-${task.status}`}>{task.status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Training View */}
        {view === 'training' && (
          <div className="training-view">
            <div className="skills-panel">
              <h4>Skill Development</h4>
              <div className="skills-list">
                {skills.map((skill) => (
                  <div key={skill.name} className="skill-card">
                    <div className="skill-header">
                      <span className="skill-name">{skill.name}</span>
                      <span className={`skill-trend trend-${skill.trend}`}>
                        {skill.trend === 'up' ? '↑' : skill.trend === 'down' ? '↓' : '→'}
                      </span>
                    </div>
                    <div className="skill-progress">
                      <div className="skill-bar">
                        <div className="skill-fill" style={{ width: `${skill.level}%`, background: getSkillColor(skill.level) }}></div>
                      </div>
                      <span className="skill-level">{skill.level}%</span>
                    </div>
                    <div className="skill-experience">
                      <span>{skill.experience} XP</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="training-actions">
              <h4>Training Actions</h4>
              <div className="action-form" style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', marginBottom: '6px' }}>Study topic</label>
                <input
                  type="text"
                  value={studyTopic}
                  onChange={(e) => setStudyTopic(e.target.value)}
                  placeholder="e.g., Python decorators"
                  style={{ width: '100%', marginBottom: '10px' }}
                />
                <label style={{ display: 'block', marginBottom: '6px' }}>Practice skill</label>
                <input
                  type="text"
                  value={practiceSkillName}
                  onChange={(e) => setPracticeSkillName(e.target.value)}
                  placeholder="e.g., Python programming"
                  style={{ width: '100%', marginBottom: '10px' }}
                />
                <label style={{ display: 'block', marginBottom: '6px' }}>Practice task</label>
                <input
                  type="text"
                  value={practiceTaskDescription}
                  onChange={(e) => setPracticeTaskDescription(e.target.value)}
                  placeholder="e.g., Write a factorial function"
                  style={{ width: '100%' }}
                />
              </div>
              <div className="action-buttons">
                <button className="btn-action" onClick={handleSubmitStudyTask}>
                  📖 Start Study Session
                </button>
                <button className="btn-action" onClick={handleSubmitPracticeTask}>
                  ⚡ Start Practice Session
                </button>
              </div>
              {trainingActionStatus && (
                <div className={`training-action-status ${trainingActionStatus.type}`} style={{ marginTop: '10px' }}>
                  {trainingActionStatus.message}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Memory View */}
        {view === 'memory' && (
          <div className="memory-view">
            <div className="memory-stats-panel">
              <h4>Learning Memory Statistics</h4>
              {memoryStats && (
                <div className="memory-grid">
                  <div className="memory-stat">
                    <span className="memory-value">{memoryStats.total_experiences}</span>
                    <span className="memory-label">Total Experiences</span>
                  </div>
                  <div className="memory-stat positive">
                    <span className="memory-value">{memoryStats.positive_feedback}</span>
                    <span className="memory-label">Positive Feedback</span>
                  </div>
                  <div className="memory-stat negative">
                    <span className="memory-value">{memoryStats.negative_feedback}</span>
                    <span className="memory-label">Negative Feedback</span>
                  </div>
                  <div className="memory-stat">
                    <span className="memory-value">{memoryStats.snapshots_count}</span>
                    <span className="memory-label">Snapshots</span>
                  </div>
                </div>
              )}
            </div>

            <div className="memory-actions">
              <h4>Memory Management</h4>
              <div className="action-row">
                <button className="btn-snapshot" onClick={handleCreateSnapshot}>
                  📸 Create Snapshot
                </button>
                <button className="btn-export" onClick={() => fetch('/learning-memory/export-training-data', { method: 'POST' })}>
                  📤 Export Training Data
                </button>
                <button className="btn-decay" onClick={() => fetch('/learning-memory/decay-trust-scores', { method: 'POST' })}>
                  📉 Apply Trust Decay
                </button>
              </div>
              {memoryStats && (
                <div className="last-snapshot">
                  <span>Last Snapshot: {formatDate(memoryStats.last_snapshot)}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LearningTab;
