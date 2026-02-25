/**
 * Grace Todos Tab - Autonomous Task Management System
 *
 * Features:
 * - Track all Grace autonomous actions across the system
 * - Drag & drop task prioritization
 * - Sub-agents and multi-threading visualization
 * - Team management with skill-based auto-assignment
 * - User requirements panel with Genesis ID
 * - Notion-style panels and boards
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { API_BASE } from '../config/api';
import './GraceTodosTab.css';

// ============================================================================
// Constants
// ============================================================================

const TASK_STATUSES = [
  { id: 'queued', label: 'Queued', color: '#6b7280', icon: '📋' },
  { id: 'scheduled', label: 'Scheduled', color: '#8b5cf6', icon: '📅' },
  { id: 'running', label: 'Running', color: '#3b82f6', icon: '⚡' },
  { id: 'paused', label: 'Paused', color: '#f59e0b', icon: '⏸️' },
  { id: 'completed', label: 'Completed', color: '#10b981', icon: '✅' },
  { id: 'failed', label: 'Failed', color: '#ef4444', icon: '❌' },
];

const TASK_PRIORITIES = [
  { id: 'critical', label: 'Critical', color: '#dc2626' },
  { id: 'high', label: 'High', color: '#f97316' },
  { id: 'medium', label: 'Medium', color: '#eab308' },
  { id: 'low', label: 'Low', color: '#22c55e' },
  { id: 'background', label: 'Background', color: '#6b7280' },
];

const TASK_TYPES = [
  { id: 'autonomous', label: 'Autonomous', icon: '🤖' },
  { id: 'user_request', label: 'User Request', icon: '👤' },
  { id: 'scheduled', label: 'Scheduled', icon: '⏰' },
  { id: 'sub_agent', label: 'Sub-Agent', icon: '🔗' },
  { id: 'learning', label: 'Learning', icon: '📚' },
  { id: 'diagnostic', label: 'Diagnostic', icon: '🔍' },
  { id: 'healing', label: 'Healing', icon: '💊' },
  { id: 'memory', label: 'Memory', icon: '🧠' },
  { id: 'analysis', label: 'Analysis', icon: '📊' },
  { id: 'ingestion', label: 'Ingestion', icon: '📥' },
];

const PROCESSING_MODES = [
  { id: 'sequential', label: 'Sequential', icon: '→' },
  { id: 'parallel', label: 'Parallel', icon: '⇉' },
  { id: 'background', label: 'Background', icon: '◐' },
  { id: 'multi_thread', label: 'Multi-Thread', icon: '⫘' },
  { id: 'distributed', label: 'Distributed', icon: '⬡' },
];

// ============================================================================
// Sortable Task Card Component
// ============================================================================

const SortableTaskCard = ({ task, onEdit, onExecute, onPause, onCancel }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.genesis_key_id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const priority = TASK_PRIORITIES.find(p => p.id === task.priority);
  const taskType = TASK_TYPES.find(t => t.id === task.task_type);
  const processingMode = PROCESSING_MODES.find(m => m.id === task.processing_mode);

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`grace-task-card ${isDragging ? 'dragging' : ''}`}
    >
      <div className="task-header">
        <span className="task-type-icon" title={taskType?.label}>
          {taskType?.icon || '📋'}
        </span>
        <span
          className="task-priority"
          style={{ backgroundColor: priority?.color }}
          title={priority?.label}
        >
          {priority?.label?.charAt(0)}
        </span>
        <span className="task-mode" title={processingMode?.label}>
          {processingMode?.icon}
        </span>
      </div>

      <div className="task-title">{task.title}</div>

      {task.description && (
        <div className="task-description">{task.description}</div>
      )}

      {task.status === 'running' && (
        <div className="task-progress">
          <div
            className="progress-bar"
            style={{ width: `${task.progress_percent}%` }}
          />
          <span className="progress-text">{task.progress_percent}%</span>
          {task.current_step && (
            <span className="current-step">{task.current_step}</span>
          )}
        </div>
      )}

      {task.assignee_genesis_id && (
        <div className="task-assignee">
          <span className="assignee-icon">👤</span>
          <span className="assignee-id">{task.assignee_genesis_id.slice(0, 12)}...</span>
        </div>
      )}

      {task.assigned_agent && (
        <div className="task-agent">
          <span className="agent-icon">🤖</span>
          <span className="agent-id">{task.assigned_agent.slice(0, 12)}...</span>
        </div>
      )}

      <div className="task-meta">
        <span className="task-id" title={task.genesis_key_id}>
          {task.genesis_key_id?.slice(0, 10)}...
        </span>
        {task.sub_task_ids?.length > 0 && (
          <span className="subtask-count">
            🔗 {task.sub_task_ids.length} subtasks
          </span>
        )}
      </div>

      <div className="task-actions">
        <button onClick={() => onEdit(task)} title="Edit">✏️</button>
        {task.status === 'queued' && (
          <button onClick={() => onExecute(task.genesis_key_id)} title="Execute">▶️</button>
        )}
        {task.status === 'running' && (
          <button onClick={() => onPause(task.genesis_key_id)} title="Pause">⏸️</button>
        )}
        {(task.status === 'running' || task.status === 'queued') && (
          <button onClick={() => onCancel(task.genesis_key_id)} title="Cancel">🛑</button>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Kanban Column Component
// ============================================================================

const KanbanColumn = ({ status, tasks, onEdit, onExecute, onPause, onCancel }) => {
  const statusConfig = TASK_STATUSES.find(s => s.id === status);
  const taskIds = tasks.map(t => t.genesis_key_id);

  return (
    <div className="kanban-column" data-status={status}>
      <div className="column-header" style={{ borderColor: statusConfig?.color }}>
        <span className="column-icon">{statusConfig?.icon}</span>
        <span className="column-title">{statusConfig?.label}</span>
        <span className="column-count">{tasks.length}</span>
      </div>

      <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
        <div className="column-content">
          {tasks.map(task => (
            <SortableTaskCard
              key={task.genesis_key_id}
              task={task}
              onEdit={onEdit}
              onExecute={onExecute}
              onPause={onPause}
              onCancel={onCancel}
            />
          ))}
        </div>
      </SortableContext>
    </div>
  );
};

// ============================================================================
// Grace Thinking Panel Component
// ============================================================================

const GraceThinkingPanel = ({ thinking }) => {
  if (!thinking) return null;

  return (
    <div className="grace-thinking-panel">
      <div className="thinking-header">
        <span className="thinking-icon">🧠</span>
        <span className="thinking-title">Grace is thinking...</span>
        <span className="thinking-load">
          Load: {thinking.current_load}%
        </span>
      </div>

      <div className="thinking-thoughts">
        {thinking.current_thoughts?.map((thought, idx) => (
          <div key={idx} className="thought-item">
            <div className="thought-title">{thought.title}</div>
            <div className="thought-progress">
              <div
                className="thought-bar"
                style={{ width: `${thought.progress}%` }}
              />
            </div>
            {thought.current_step && (
              <div className="thought-step">{thought.current_step}</div>
            )}
          </div>
        ))}
      </div>

      <div className="thinking-stats">
        <span>Pending: {thinking.pending_thoughts}</span>
        <span>Agents: {thinking.agents_active}</span>
      </div>
    </div>
  );
};

// ============================================================================
// Team Panel Component
// ============================================================================

const TeamPanel = ({ team, onAssign: _onAssign, onAddMember }) => {
  return (
    <div className="team-panel">
      <div className="panel-header">
        <span className="panel-title">👥 Team</span>
        <button className="add-btn" onClick={onAddMember}>+ Add</button>
      </div>

      <div className="team-list">
        {team.map(member => (
          <div
            key={member.genesis_key_id}
            className={`team-member ${member.is_active ? 'active' : 'inactive'}`}
          >
            <div className="member-avatar">
              {member.is_agent ? '🤖' : '👤'}
            </div>
            <div className="member-info">
              <div className="member-name">{member.display_name || member.name}</div>
              <div className="member-role">{member.role}</div>
              <div className="member-load">
                Load: {member.current_load}% / {member.capacity}%
              </div>
            </div>
            <div className="member-skills">
              {member.skill_sets?.slice(0, 3).map((skill, idx) => (
                <span key={idx} className="skill-tag">{skill}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// Requirements Panel Component
// ============================================================================

const RequirementsPanel = ({ requirements, onCreateRequirement, onGenerateTasks }) => {
  return (
    <div className="requirements-panel">
      <div className="panel-header">
        <span className="panel-title">📝 User Requirements</span>
        <button className="add-btn" onClick={onCreateRequirement}>+ New</button>
      </div>

      <div className="requirements-list">
        {requirements.map(req => (
          <div key={req.genesis_key_id} className="requirement-card">
            <div className="req-header">
              <span className="req-user">
                👤 {req.user_genesis_id?.slice(0, 10)}...
              </span>
              <span className={`req-status ${req.status}`}>{req.status}</span>
            </div>
            <div className="req-title">{req.title}</div>
            <div className="req-description">{req.description}</div>
            <div className="req-items">
              {req.requirements?.slice(0, 3).map((item, idx) => (
                <div key={idx} className="req-item">• {item}</div>
              ))}
              {req.requirements?.length > 3 && (
                <div className="req-more">+{req.requirements.length - 3} more</div>
              )}
            </div>
            <div className="req-actions">
              {req.status === 'active' && (
                <button onClick={() => onGenerateTasks(req.genesis_key_id)}>
                  🚀 Generate Tasks
                </button>
              )}
              {req.generated_tasks?.length > 0 && (
                <span className="req-tasks">
                  {req.generated_tasks.length} tasks generated
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// Agents Panel Component
// ============================================================================

const AgentsPanel = ({ agents, onCreateAgent }) => {
  return (
    <div className="agents-panel">
      <div className="panel-header">
        <span className="panel-title">🤖 Grace Agents</span>
        <button className="add-btn" onClick={onCreateAgent}>+ Add</button>
      </div>

      <div className="agents-list">
        {agents.map(agent => (
          <div
            key={agent.agent_id}
            className={`agent-card ${agent.status}`}
          >
            <div className="agent-header">
              <span className="agent-name">{agent.name}</span>
              <span className={`agent-status ${agent.status}`}>
                {agent.status}
              </span>
            </div>
            <div className="agent-type">{agent.agent_type}</div>
            <div className="agent-capabilities">
              {agent.capabilities?.map((cap, idx) => (
                <span key={idx} className="capability-tag">{cap}</span>
              ))}
            </div>
            <div className="agent-stats">
              <span>Processed: {agent.total_processed}</span>
              <span>Success: {(agent.success_rate * 100).toFixed(0)}%</span>
              <span>Queue: {agent.task_queue?.length || 0}</span>
            </div>
            {agent.current_task_id && (
              <div className="agent-current">
                Working on: {agent.current_task_id.slice(0, 10)}...
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// Task Modal Component
// ============================================================================

const TaskModal = ({ task, isOpen, onClose, onSave }) => {
  const [formData, setFormData] = useState(task || {
    title: '',
    description: '',
    task_type: 'autonomous',
    priority: 'medium',
    processing_mode: 'sequential',
    labels: [],
    notes: '',
  });

  useEffect(() => {
    if (task) queueMicrotask(() => setFormData(task));
  }, [task]);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{task?.genesis_key_id ? 'Edit Task' : 'New Task'}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Title</label>
            <input
              type="text"
              value={formData.title}
              onChange={e => setFormData({ ...formData, title: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Type</label>
              <select
                value={formData.task_type}
                onChange={e => setFormData({ ...formData, task_type: e.target.value })}
              >
                {TASK_TYPES.map(type => (
                  <option key={type.id} value={type.id}>
                    {type.icon} {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Priority</label>
              <select
                value={formData.priority}
                onChange={e => setFormData({ ...formData, priority: e.target.value })}
              >
                {TASK_PRIORITIES.map(priority => (
                  <option key={priority.id} value={priority.id}>
                    {priority.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Processing Mode</label>
              <select
                value={formData.processing_mode}
                onChange={e => setFormData({ ...formData, processing_mode: e.target.value })}
              >
                {PROCESSING_MODES.map(mode => (
                  <option key={mode.id} value={mode.id}>
                    {mode.icon} {mode.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Labels (comma separated)</label>
            <input
              type="text"
              value={formData.labels?.join(', ') || ''}
              onChange={e => setFormData({
                ...formData,
                labels: e.target.value.split(',').map(l => l.trim()).filter(Boolean)
              })}
            />
          </div>

          <div className="form-group">
            <label>Notes</label>
            <textarea
              value={formData.notes}
              onChange={e => setFormData({ ...formData, notes: e.target.value })}
            />
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary">Save Task</button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ============================================================================
// Main Grace Todos Tab Component
// ============================================================================

const GraceTodosTab = () => {
  // State
  const [board, setBoard] = useState({
    queued: [],
    scheduled: [],
    running: [],
    paused: [],
    completed: [],
    failed: [],
  });
  const [stats, setStats] = useState(null);
  const [thinking, setThinking] = useState(null);
  const [team, setTeam] = useState([]);
  const [requirements, setRequirements] = useState([]);
  const [agents, setAgents] = useState([]);
  const [activeTask, setActiveTask] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activePanel, setActivePanel] = useState('board'); // board, team, requirements, agents
  const [isLoading, setIsLoading] = useState(true);
  const [ws, setWs] = useState(null);

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const fetchBoard = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/grace-todos/board`);
      const data = await response.json();
      setBoard(data);
    } catch (error) {
      console.error('Failed to fetch board:', error);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/grace-todos/board/stats`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  }, []);

  const fetchThinking = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/grace-todos/grace/thinking`);
      const data = await response.json();
      setThinking(data);
    } catch (error) {
      console.error('Failed to fetch thinking:', error);
    }
  }, []);

  const fetchTeam = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/grace-todos/team`);
      const data = await response.json();
      setTeam(data);
    } catch (error) {
      console.error('Failed to fetch team:', error);
    }
  }, []);

  const fetchRequirements = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/grace-todos/requirements`);
      const data = await response.json();
      setRequirements(data);
    } catch (error) {
      console.error('Failed to fetch requirements:', error);
    }
  }, []);

  const fetchAgents = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/grace-todos/agents`);
      const data = await response.json();
      setAgents(data);
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      await Promise.all([
        fetchBoard(),
        fetchStats(),
        fetchThinking(),
        fetchTeam(),
        fetchRequirements(),
        fetchAgents(),
      ]);
      setIsLoading(false);
    };

    loadData();

    // Set up polling
    const pollInterval = setInterval(() => {
      fetchBoard();
      fetchThinking();
      fetchStats();
    }, 5000);

    return () => clearInterval(pollInterval);
  }, [fetchBoard, fetchStats, fetchThinking, fetchTeam, fetchRequirements, fetchAgents]);

  const handleWSMessage = (message) => {
    switch (message.type) {
      case 'task_created':
      case 'task_updated':
      case 'task_moved':
      case 'task_completed':
      case 'task_failed':
        fetchBoard();
        fetchStats();
        break;
      case 'task_progress':
        // Update specific task progress
        setBoard(prev => {
          const newBoard = { ...prev };
          for (const column of Object.values(newBoard)) {
            const task = column.find(t => t.genesis_key_id === message.data.task_id);
            if (task) {
              task.progress_percent = message.data.progress;
              task.current_step = message.data.step;
              break;
            }
          }
          return newBoard;
        });
        break;
      case 'agent_created':
      case 'agent_updated':
        fetchAgents();
        break;
      case 'team_member_added':
        fetchTeam();
        break;
      default:
        break;
    }
  };

  // WebSocket connection
  useEffect(() => {
    const connectWS = () => {
      const websocket = new WebSocket(`ws://localhost:8000/api/grace-todos/ws`);

      websocket.onopen = () => {
        console.log('Grace Todos WebSocket connected');
        websocket.send(JSON.stringify({
          type: 'subscribe',
          channels: ['tasks', 'agents', 'team']
        }));
      };

      websocket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWSMessage(message);
      };

      websocket.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(connectWS, 3000);
      };

      setWs(websocket);
    };

    connectWS();

    return () => {
      if (ws) ws.close();
    };
  }, []);

  // ============================================================================
  // Task Actions
  // ============================================================================

  const createTask = async (taskData) => {
    try {
      const response = await fetch(`${API_BASE}/api/grace-todos/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskData),
      });
      if (response.ok) {
        fetchBoard();
        fetchStats();
      }
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const updateTask = async (taskId, updates) => {
    try {
      const response = await fetch(`${API_BASE}/api/grace-todos/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (response.ok) {
        fetchBoard();
      }
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

  const moveTask = async (taskId, newStatus, position) => {
    try {
      const response = await fetch(`${API_BASE}/api/grace-todos/tasks/${taskId}/move?new_status=${newStatus}&position=${position}`, {
        method: 'POST',
      });
      if (response.ok) {
        fetchBoard();
      }
    } catch (error) {
      console.error('Failed to move task:', error);
    }
  };

  const executeTask = async (taskId) => {
    try {
      await fetch(`${API_BASE}/api/grace-todos/tasks/${taskId}/execute`, {
        method: 'POST',
      });
      fetchBoard();
    } catch (error) {
      console.error('Failed to execute task:', error);
    }
  };

  const pauseTask = async (taskId) => {
    try {
      await fetch(`${API_BASE}/api/grace-todos/tasks/${taskId}/pause`, {
        method: 'POST',
      });
      fetchBoard();
    } catch (error) {
      console.error('Failed to pause task:', error);
    }
  };

  const cancelTask = async (taskId) => {
    try {
      await fetch(`${API_BASE}/api/grace-todos/tasks/${taskId}/cancel`, {
        method: 'POST',
      });
      fetchBoard();
    } catch (error) {
      console.error('Failed to cancel task:', error);
    }
  };

  const generateTasksFromRequirement = async (reqId) => {
    try {
      await fetch(`${API_BASE}/api/grace-todos/requirements/${reqId}/generate-tasks`, {
        method: 'POST',
      });
      fetchBoard();
      fetchRequirements();
    } catch (error) {
      console.error('Failed to generate tasks:', error);
    }
  };

  const reprioritizeTasks = async () => {
    try {
      await fetch(`${API_BASE}/api/grace-todos/grace/prioritize`, {
        method: 'POST',
      });
      fetchBoard();
    } catch (error) {
      console.error('Failed to reprioritize:', error);
    }
  };

  // ============================================================================
  // Drag & Drop Handlers
  // ============================================================================

  const handleDragEnd = (event) => {
    const { active, over } = event;

    if (!over) return;

    const activeId = active.id;
    const overId = over.id;

    // Find which column the task is being dropped into
    let targetStatus = null;
    let targetIndex = 0;

    for (const [status, tasks] of Object.entries(board)) {
      const idx = tasks.findIndex(t => t.genesis_key_id === overId);
      if (idx !== -1) {
        targetStatus = status;
        targetIndex = idx;
        break;
      }
      // Check if dropping on column itself
      if (overId === status) {
        targetStatus = status;
        targetIndex = tasks.length;
        break;
      }
    }

    if (targetStatus) {
      moveTask(activeId, targetStatus, targetIndex);
    }
  };

  // ============================================================================
  // Render
  // ============================================================================

  if (isLoading) {
    return (
      <div className="grace-todos-loading">
        <div className="loading-spinner">🧠</div>
        <div>Loading Grace Todos...</div>
      </div>
    );
  }

  return (
    <div className="grace-todos-container">
      {/* Header */}
      <div className="grace-todos-header">
        <div className="header-title">
          <span className="header-icon">🧠</span>
          <h1>Grace Todos</h1>
          <span className="header-subtitle">Autonomous Task Management</span>
        </div>

        <div className="header-stats">
          <div className="stat">
            <span className="stat-value">{stats?.total || 0}</span>
            <span className="stat-label">Total</span>
          </div>
          <div className="stat">
            <span className="stat-value">{stats?.autonomous_active || 0}</span>
            <span className="stat-label">Active</span>
          </div>
          <div className="stat">
            <span className="stat-value">
              {((stats?.completion_rate || 0) * 100).toFixed(0)}%
            </span>
            <span className="stat-label">Completed</span>
          </div>
        </div>

        <div className="header-actions">
          <button
            className="action-btn primary"
            onClick={() => {
              setActiveTask(null);
              setIsModalOpen(true);
            }}
          >
            + New Task
          </button>
          <button className="action-btn" onClick={reprioritizeTasks}>
            🔄 Reprioritize
          </button>
        </div>
      </div>

      {/* Grace Thinking Panel */}
      <GraceThinkingPanel thinking={thinking} />

      {/* Navigation Tabs */}
      <div className="panel-tabs">
        <button
          className={`tab ${activePanel === 'board' ? 'active' : ''}`}
          onClick={() => setActivePanel('board')}
        >
          📋 Board
        </button>
        <button
          className={`tab ${activePanel === 'team' ? 'active' : ''}`}
          onClick={() => setActivePanel('team')}
        >
          👥 Team ({team.length})
        </button>
        <button
          className={`tab ${activePanel === 'requirements' ? 'active' : ''}`}
          onClick={() => setActivePanel('requirements')}
        >
          📝 Requirements ({requirements.length})
        </button>
        <button
          className={`tab ${activePanel === 'agents' ? 'active' : ''}`}
          onClick={() => setActivePanel('agents')}
        >
          🤖 Agents ({agents.length})
        </button>
      </div>

      {/* Main Content */}
      <div className="grace-todos-content">
        {activePanel === 'board' && (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragEnd={handleDragEnd}
          >
            <div className="kanban-board">
              {TASK_STATUSES.map(status => (
                <KanbanColumn
                  key={status.id}
                  status={status.id}
                  tasks={board[status.id] || []}
                  onEdit={(task) => {
                    setActiveTask(task);
                    setIsModalOpen(true);
                  }}
                  onExecute={executeTask}
                  onPause={pauseTask}
                  onCancel={cancelTask}
                />
              ))}
            </div>
          </DndContext>
        )}

        {activePanel === 'team' && (
          <TeamPanel
            team={team}
            onAddMember={() => console.log('Add member')}
          />
        )}

        {activePanel === 'requirements' && (
          <RequirementsPanel
            requirements={requirements}
            onCreateRequirement={() => console.log('Create requirement')}
            onGenerateTasks={generateTasksFromRequirement}
          />
        )}

        {activePanel === 'agents' && (
          <AgentsPanel
            agents={agents}
            onCreateAgent={() => console.log('Create agent')}
          />
        )}
      </div>

      {/* Task Modal */}
      <TaskModal
        task={activeTask}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setActiveTask(null);
        }}
        onSave={(data) => {
          if (activeTask?.genesis_key_id) {
            updateTask(activeTask.genesis_key_id, data);
          } else {
            createTask(data);
          }
        }}
      />
    </div>
  );
};

export default GraceTodosTab;
