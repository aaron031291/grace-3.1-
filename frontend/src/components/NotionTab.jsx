import { useEffect, useState, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import "./NotionTab.css";

const API_BASE = "http://localhost:8000";

// Status mapping for columns
const STATUS_MAP = {
  "col-todo": "todo",
  "col-progress": "in_progress",
  "col-review": "in_review",
  "col-done": "completed",
};

const COLUMN_TO_STATUS = {
  todo: "col-todo",
  in_progress: "col-progress",
  in_review: "col-review",
  completed: "col-done",
};

const PRIORITY_COLORS = {
  low: "#10b981",
  medium: "#f59e0b",
  high: "#f97316",
  critical: "#ef4444",
};

const TYPE_ICONS = {
  learning: "brain",
  building: "hammer",
  research: "magnifier",
  maintenance: "wrench",
  experiment: "flask",
  documentation: "book",
  analysis: "chart",
  other: "puzzle",
};

// Task Card Component
function DraggableCard({ task, columnId, onDelete, onEdit, profiles }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: task.genesis_key_id,
    data: { type: "card", task, columnId },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    borderLeftColor: PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.medium,
  };

  const assignee = profiles.find(p => p.genesis_key_id === task.assignee_genesis_key_id);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`kanban-card priority-${task.priority}`}
      {...attributes}
      {...listeners}
    >
      <div className="card-content">
        <div className="card-header-row">
          <span className={`task-type-badge type-${task.task_type}`}>
            {task.task_type}
          </span>
          <span className={`priority-badge priority-${task.priority}`}>
            {task.priority}
          </span>
        </div>
        <h4>{task.title}</h4>
        {task.description && (
          <p className="card-description">{task.description}</p>
        )}
        <div className="card-meta">
          {assignee && (
            <span className="assignee-badge" title={`Assigned to ${assignee.name}`}>
              {assignee.display_name || assignee.name}
            </span>
          )}
          {task.folder_path && (
            <span className="folder-badge" title={task.folder_path}>
              {task.folder_path.split('/').pop() || 'root'}
            </span>
          )}
          {task.progress_percent > 0 && task.progress_percent < 100 && (
            <div className="progress-bar-mini">
              <div
                className="progress-fill"
                style={{ width: `${task.progress_percent}%` }}
              />
            </div>
          )}
        </div>
        <div className="card-footer">
          <span className="genesis-key" title={task.genesis_key_id}>
            {task.genesis_key_id.slice(0, 12)}...
          </span>
          <span className="version-badge">v{task.version}</span>
        </div>
      </div>
      <div className="card-actions">
        <button
          className="card-edit"
          onClick={(e) => {
            e.stopPropagation();
            onEdit(task);
          }}
          onPointerDown={(e) => e.stopPropagation()}
          title="Edit task"
        >
          ...
        </button>
        <button
          className="card-delete"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(task.genesis_key_id);
          }}
          onPointerDown={(e) => e.stopPropagation()}
          title="Delete task"
        >
          x
        </button>
      </div>
    </div>
  );
}

// Column Component
function Column({ column, tasks, onDelete, onEdit, activeId: _activeId, profiles }) {
  const taskIds = tasks.map((t) => t.genesis_key_id);
  const { setNodeRef } = useSortable({
    id: column.id,
    data: { type: "column", column },
    disabled: true,
  });

  return (
    <div ref={setNodeRef} className={`kanban-column`}>
      <div className="column-header">
        <h3>{column.title}</h3>
        <span className="card-count">{tasks.length}</span>
      </div>

      <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
        <div className="cards-list">
          {tasks.length === 0 ? (
            <div className="empty-column">Drop tasks here</div>
          ) : (
            tasks.map((task) => (
              <DraggableCard
                key={task.genesis_key_id}
                task={task}
                columnId={column.id}
                onDelete={onDelete}
                onEdit={onEdit}
                profiles={profiles}
              />
            ))
          )}
        </div>
      </SortableContext>
    </div>
  );
}

// Profile Card Component
function ProfileCard({ profile, onLogOn, onLogOff, onEdit }) {
  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  };

  return (
    <div className={`profile-card ${profile.is_active ? 'active' : 'inactive'}`}>
      <div className="profile-avatar">
        {profile.avatar_url ? (
          <img src={profile.avatar_url} alt={profile.name} />
        ) : (
          <div className="avatar-placeholder">
            {profile.name.charAt(0).toUpperCase()}
          </div>
        )}
        <span className={`status-indicator ${profile.is_active ? 'online' : 'offline'}`} />
      </div>
      <div className="profile-info">
        <h4>{profile.display_name || profile.name}</h4>
        <span className="genesis-id">{profile.genesis_key_id}</span>
        <div className="profile-stats">
          <span title="Tasks completed">{profile.tasks_completed} done</span>
          <span title="In progress">{profile.tasks_in_progress} active</span>
          <span title="Total time logged">{formatTime(profile.total_time_logged)}</span>
        </div>
        {profile.skill_set && profile.skill_set.length > 0 && (
          <div className="profile-skills">
            {profile.skill_set.slice(0, 3).map((skill, i) => (
              <span key={i} className="skill-tag">{skill}</span>
            ))}
          </div>
        )}
      </div>
      <div className="profile-actions">
        {profile.is_active ? (
          <button onClick={() => onLogOff(profile.genesis_key_id)} className="log-btn log-off">
            Log Off
          </button>
        ) : (
          <button onClick={() => onLogOn(profile.genesis_key_id)} className="log-btn log-on">
            Log On
          </button>
        )}
        <button onClick={() => onEdit(profile)} className="edit-btn">
          Edit
        </button>
      </div>
    </div>
  );
}

// Task Modal Component
function TaskModal({ task, profiles, folders, onSave, onClose, isNew }) {
  const [formData, setFormData] = useState(
    task || {
      title: "",
      description: "",
      status: "todo",
      priority: "medium",
      task_type: "other",
      assignee_genesis_key_id: "",
      folder_path: "",
      labels: [],
      notes: "",
      estimated_hours: null,
    }
  );
  const [newLabel, setNewLabel] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const addLabel = () => {
    if (newLabel.trim() && !formData.labels?.includes(newLabel.trim())) {
      setFormData({
        ...formData,
        labels: [...(formData.labels || []), newLabel.trim()],
      });
      setNewLabel("");
    }
  };

  const removeLabel = (label) => {
    setFormData({
      ...formData,
      labels: formData.labels.filter((l) => l !== label),
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content task-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{isNew ? "Create New Task" : "Edit Task"}</h3>
          <button className="modal-close" onClick={onClose}>x</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Title *</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
              placeholder="Enter task title..."
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={formData.description || ""}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe what needs to be done..."
              rows={3}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              >
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="in_review">In Review</option>
                <option value="completed">Completed</option>
              </select>
            </div>

            <div className="form-group">
              <label>Priority</label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div className="form-group">
              <label>Type</label>
              <select
                value={formData.task_type}
                onChange={(e) => setFormData({ ...formData, task_type: e.target.value })}
              >
                <option value="learning">Learning</option>
                <option value="building">Building</option>
                <option value="research">Research</option>
                <option value="maintenance">Maintenance</option>
                <option value="experiment">Experiment</option>
                <option value="documentation">Documentation</option>
                <option value="analysis">Analysis</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Assign To</label>
              <select
                value={formData.assignee_genesis_key_id || ""}
                onChange={(e) => setFormData({ ...formData, assignee_genesis_key_id: e.target.value })}
              >
                <option value="">Unassigned</option>
                {profiles.map((p) => (
                  <option key={p.genesis_key_id} value={p.genesis_key_id}>
                    {p.display_name || p.name} ({p.genesis_key_id.slice(0, 8)}...)
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Folder Path</label>
              <select
                value={formData.folder_path || ""}
                onChange={(e) => setFormData({ ...formData, folder_path: e.target.value })}
              >
                <option value="">No folder</option>
                {folders.map((f) => (
                  <option key={f} value={f}>{f || "root"}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Estimated Hours</label>
              <input
                type="number"
                min="0"
                step="0.5"
                value={formData.estimated_hours || ""}
                onChange={(e) => setFormData({ ...formData, estimated_hours: parseFloat(e.target.value) || null })}
                placeholder="Hours"
              />
            </div>
          </div>

          <div className="form-group">
            <label>Labels</label>
            <div className="labels-input">
              <input
                type="text"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addLabel())}
                placeholder="Add label..."
              />
              <button type="button" onClick={addLabel}>+</button>
            </div>
            <div className="labels-list">
              {formData.labels?.map((label) => (
                <span key={label} className="label-tag">
                  {label}
                  <button type="button" onClick={() => removeLabel(label)}>x</button>
                </span>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Notes</label>
            <textarea
              value={formData.notes || ""}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Additional notes..."
              rows={2}
            />
          </div>

          {!isNew && formData.genesis_key_id && (
            <div className="task-provenance">
              <h4>Provenance</h4>
              <div className="provenance-info">
                <span>Genesis Key: {formData.genesis_key_id}</span>
                <span>Version: {formData.version}</span>
                <span>Created: {new Date(formData.created_at).toLocaleString()}</span>
                <span>Updated: {new Date(formData.updated_at).toLocaleString()}</span>
              </div>
            </div>
          )}

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              {isNew ? "Create Task" : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Profile Modal Component
function ProfileModal({ profile, onSave, onClose, isNew }) {
  const [formData, setFormData] = useState(
    profile || {
      name: "",
      display_name: "",
      skill_set: [],
      specializations: [],
    }
  );
  const [newSkill, setNewSkill] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const addSkill = () => {
    if (newSkill.trim() && !formData.skill_set?.includes(newSkill.trim())) {
      setFormData({
        ...formData,
        skill_set: [...(formData.skill_set || []), newSkill.trim()],
      });
      setNewSkill("");
    }
  };

  const removeSkill = (skill) => {
    setFormData({
      ...formData,
      skill_set: formData.skill_set.filter((s) => s !== skill),
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content profile-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{isNew ? "Create New Profile" : "Edit Profile"}</h3>
          <button className="modal-close" onClick={onClose}>x</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              placeholder="Profile name..."
            />
          </div>

          <div className="form-group">
            <label>Display Name</label>
            <input
              type="text"
              value={formData.display_name || ""}
              onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              placeholder="Display name..."
            />
          </div>

          <div className="form-group">
            <label>Skills</label>
            <div className="labels-input">
              <input
                type="text"
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addSkill())}
                placeholder="Add skill..."
              />
              <button type="button" onClick={addSkill}>+</button>
            </div>
            <div className="labels-list">
              {formData.skill_set?.map((skill) => (
                <span key={skill} className="label-tag">
                  {skill}
                  <button type="button" onClick={() => removeSkill(skill)}>x</button>
                </span>
              ))}
            </div>
          </div>

          {!isNew && formData.genesis_key_id && (
            <div className="profile-provenance">
              <h4>Profile Info</h4>
              <div className="provenance-info">
                <span>Genesis Key: {formData.genesis_key_id}</span>
                <span>Created: {new Date(formData.created_at).toLocaleString()}</span>
                <span>Tasks Completed: {formData.tasks_completed}</span>
                <span>Total Time: {Math.floor(formData.total_time_logged / 3600)}h</span>
              </div>
            </div>
          )}

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              {isNew ? "Create Profile" : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// History Modal Component
function HistoryModal({ task, history, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content history-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Task History: {task.title}</h3>
          <button className="modal-close" onClick={onClose}>x</button>
        </div>
        <div className="history-list">
          {history.length === 0 ? (
            <p className="no-history">No history available</p>
          ) : (
            history.map((entry) => (
              <div key={entry.id} className="history-entry">
                <div className="history-action">
                  <span className="action-type">{entry.action}</span>
                  {entry.field_changed && (
                    <span className="field-changed">{entry.field_changed}</span>
                  )}
                </div>
                {entry.old_value && entry.new_value && (
                  <div className="history-change">
                    <span className="old-value">{entry.old_value}</span>
                    <span className="arrow">-&gt;</span>
                    <span className="new-value">{entry.new_value}</span>
                  </div>
                )}
                <div className="history-meta">
                  <span>v{entry.version_number}</span>
                  <span>{new Date(entry.created_at).toLocaleString()}</span>
                  {entry.actor_name && <span>by {entry.actor_name}</span>}
                </div>
                {entry.change_reason && (
                  <div className="history-reason">{entry.change_reason}</div>
                )}
              </div>
            ))
          )}
        </div>
        <div className="modal-actions">
          <button onClick={onClose} className="btn-secondary">Close</button>
        </div>
      </div>
    </div>
  );
}

// Main NotionTab Component
export default function NotionTab() {
  const [board, setBoard] = useState({
    todo: [],
    in_progress: [],
    in_review: [],
    completed: [],
  });
  const [profiles, setProfiles] = useState([]);
  const [folders, setFolders] = useState([""]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const [stats, setStats] = useState(null);

  // Modal states
  const [taskModal, setTaskModal] = useState({ open: false, task: null, isNew: false });
  const [profileModal, setProfileModal] = useState({ open: false, profile: null, isNew: false });
  const [historyModal, setHistoryModal] = useState({ open: false, task: null, history: [] });

  // View toggle
  const [showProfiles, setShowProfiles] = useState(true);

  const columns = [
    { id: "col-todo", title: "To Do", status: "todo" },
    { id: "col-progress", title: "In Progress", status: "in_progress" },
    { id: "col-review", title: "In Review", status: "in_review" },
    { id: "col-done", title: "Completed", status: "completed" },
  ];

  // Fetch board data
  const fetchBoard = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/notion/board`);
      if (!response.ok) throw new Error("Failed to fetch board");
      const data = await response.json();

      setBoard({
        todo: data.todo || [],
        in_progress: data.in_progress || [],
        in_review: data.in_review || [],
        completed: data.completed || [],
      });
      setProfiles(data.profiles || []);
    } catch (err) {
      console.error("Error fetching board:", err);
      setError(err.message);
    }
  }, []);

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/notion/stats`);
      if (!response.ok) throw new Error("Failed to fetch stats");
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error("Error fetching stats:", err);
    }
  }, []);

  // Fetch folders from file manager
  const fetchFolders = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/files/browse?path=`);
      if (!response.ok) return;
      const data = await response.json();
      const folderPaths = data.items
        .filter((item) => item.type === "folder")
        .map((item) => item.path);
      setFolders(["", ...folderPaths]);
    } catch (err) {
      console.error("Error fetching folders:", err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchBoard(), fetchStats(), fetchFolders()]);
      setLoading(false);
    };
    loadData();
  }, [fetchBoard, fetchStats, fetchFolders]);

  // Drag sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // Find task by genesis key
  const findTask = (genesisKeyId) => {
    for (const status of Object.keys(board)) {
      const task = board[status].find((t) => t.genesis_key_id === genesisKeyId);
      if (task) return { task, status };
    }
    return null;
  };

  // Move task API call
  const moveTask = async (genesisKeyId, newStatus) => {
    try {
      const response = await fetch(
        `${API_BASE}/notion/tasks/${genesisKeyId}/move?new_status=${newStatus}`,
        { method: "POST" }
      );
      if (!response.ok) throw new Error("Failed to move task");
      return await response.json();
    } catch (err) {
      console.error("Error moving task:", err);
      throw err;
    }
  };

  // Drag handlers
  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragCancel = () => {
    setActiveId(null);
  };

  const handleDragEnd = async (event) => {
    setActiveId(null);
    const { active, over } = event;

    if (!over) return;
    if (active.id === over.id) return;

    const activeTask = findTask(active.id);
    if (!activeTask) return;

    // Determine destination
    let destStatus = null;

    // Check if dropped on a task
    const overTask = findTask(over.id);
    if (overTask) {
      destStatus = overTask.status;
    } else {
      // Check if dropped on a column
      destStatus = STATUS_MAP[over.id];
    }

    if (!destStatus || destStatus === activeTask.status) return;

    // Optimistic update
    const newBoard = { ...board };
    newBoard[activeTask.status] = newBoard[activeTask.status].filter(
      (t) => t.genesis_key_id !== active.id
    );
    const movedTask = { ...activeTask.task, status: destStatus };
    newBoard[destStatus] = [...newBoard[destStatus], movedTask];
    setBoard(newBoard);

    // API call
    try {
      await moveTask(active.id, destStatus);
      fetchBoard(); // Refresh to get updated data
    } catch {
      // Revert on error
      fetchBoard();
    }
  };

  // Task CRUD operations
  const createTask = async (taskData) => {
    try {
      const response = await fetch(`${API_BASE}/notion/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(taskData),
      });
      if (!response.ok) throw new Error("Failed to create task");
      setTaskModal({ open: false, task: null, isNew: false });
      fetchBoard();
      fetchStats();
    } catch (err) {
      console.error("Error creating task:", err);
      alert("Failed to create task: " + err.message);
    }
  };

  const updateTask = async (taskData) => {
    try {
      const response = await fetch(`${API_BASE}/notion/tasks/${taskData.genesis_key_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(taskData),
      });
      if (!response.ok) throw new Error("Failed to update task");
      setTaskModal({ open: false, task: null, isNew: false });
      fetchBoard();
      fetchStats();
    } catch (err) {
      console.error("Error updating task:", err);
      alert("Failed to update task: " + err.message);
    }
  };

  const deleteTask = async (genesisKeyId) => {
    if (!confirm("Are you sure you want to delete this task?")) return;
    try {
      const response = await fetch(`${API_BASE}/notion/tasks/${genesisKeyId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("Failed to delete task");
      fetchBoard();
      fetchStats();
    } catch (err) {
      console.error("Error deleting task:", err);
      alert("Failed to delete task: " + err.message);
    }
  };

  const _viewTaskHistory = async (task) => {
    try {
      const response = await fetch(`${API_BASE}/notion/tasks/${task.genesis_key_id}/history`);
      if (!response.ok) throw new Error("Failed to fetch history");
      const history = await response.json();
      setHistoryModal({ open: true, task, history });
    } catch (err) {
      console.error("Error fetching history:", err);
      alert("Failed to fetch task history");
    }
  };

  // Profile CRUD operations
  const generateProfile = async () => {
    try {
      const response = await fetch(`${API_BASE}/notion/profiles/generate`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Failed to generate profile");
      fetchBoard();
    } catch (err) {
      console.error("Error generating profile:", err);
      alert("Failed to generate profile: " + err.message);
    }
  };

  const createProfile = async (profileData) => {
    try {
      const response = await fetch(`${API_BASE}/notion/profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profileData),
      });
      if (!response.ok) throw new Error("Failed to create profile");
      setProfileModal({ open: false, profile: null, isNew: false });
      fetchBoard();
    } catch (err) {
      console.error("Error creating profile:", err);
      alert("Failed to create profile: " + err.message);
    }
  };

  const updateProfile = async (profileData) => {
    try {
      const response = await fetch(`${API_BASE}/notion/profiles/${profileData.genesis_key_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profileData),
      });
      if (!response.ok) throw new Error("Failed to update profile");
      setProfileModal({ open: false, profile: null, isNew: false });
      fetchBoard();
    } catch (err) {
      console.error("Error updating profile:", err);
      alert("Failed to update profile: " + err.message);
    }
  };

  const logOnProfile = async (genesisKeyId) => {
    try {
      await fetch(`${API_BASE}/notion/profiles/${genesisKeyId}/log-on`, { method: "POST" });
      fetchBoard();
    } catch (err) {
      console.error("Error logging on profile:", err);
    }
  };

  const logOffProfile = async (genesisKeyId) => {
    try {
      await fetch(`${API_BASE}/notion/profiles/${genesisKeyId}/log-off`, { method: "POST" });
      fetchBoard();
    } catch (err) {
      console.error("Error logging off profile:", err);
    }
  };

  if (loading) {
    return (
      <div className="notion-tab">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading task board...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="notion-tab">
        <div className="error-state">
          <p>Error: {error}</p>
          <button onClick={fetchBoard}>Retry</button>
        </div>
      </div>
    );
  }

  const totalTasks = Object.values(board).flat().length;

  return (
    <div className="notion-tab">
      <div className="notion-header">
        <div className="header-left">
          <h2>Grace Task Manager</h2>
          <p>Track work with Genesis Key provenance</p>
        </div>
        <div className="header-stats">
          {stats && (
            <>
              <div className="stat-item">
                <span className="stat-value">{totalTasks}</span>
                <span className="stat-label">Total Tasks</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{profiles.length}</span>
                <span className="stat-label">Profiles</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{board.in_progress.length}</span>
                <span className="stat-label">In Progress</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="notion-toolbar">
        <button
          className="btn-primary"
          onClick={() => setTaskModal({ open: true, task: null, isNew: true })}
        >
          + New Task
        </button>
        <button
          className="btn-secondary"
          onClick={() => setProfileModal({ open: true, profile: null, isNew: true })}
        >
          + New Profile
        </button>
        <button className="btn-accent" onClick={generateProfile}>
          Generate Profile Key
        </button>
        <div className="toolbar-spacer" />
        <button
          className={`btn-toggle ${showProfiles ? "active" : ""}`}
          onClick={() => setShowProfiles(!showProfiles)}
        >
          {showProfiles ? "Hide Profiles" : "Show Profiles"}
        </button>
        <button className="btn-refresh" onClick={fetchBoard}>
          Refresh
        </button>
      </div>

      {showProfiles && profiles.length > 0 && (
        <div className="profiles-section">
          <h3>Active Profiles</h3>
          <div className="profiles-grid">
            {profiles.map((profile) => (
              <ProfileCard
                key={profile.genesis_key_id}
                profile={profile}
                onLogOn={logOnProfile}
                onLogOff={logOffProfile}
                onEdit={(p) => setProfileModal({ open: true, profile: p, isNew: false })}
              />
            ))}
          </div>
        </div>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragCancel={handleDragCancel}
        onDragEnd={handleDragEnd}
      >
        <div className="kanban-container">
          {columns.map((column) => (
            <Column
              key={column.id}
              column={column}
              tasks={board[column.status] || []}
              onDelete={deleteTask}
              onEdit={(task) => setTaskModal({ open: true, task, isNew: false })}
              activeId={activeId}
              profiles={profiles}
            />
          ))}
        </div>

        <DragOverlay>
          {activeId ? (
            <div className="kanban-card dragging-overlay">
              <div className="card-content">
                <h4>{findTask(activeId)?.task?.title}</h4>
              </div>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      <div className="kanban-footer">
        <p>Drag tasks between columns to update status. All changes are tracked with Genesis Keys.</p>
      </div>

      {/* Modals */}
      {taskModal.open && (
        <TaskModal
          task={taskModal.task}
          profiles={profiles}
          folders={folders}
          onSave={taskModal.isNew ? createTask : updateTask}
          onClose={() => setTaskModal({ open: false, task: null, isNew: false })}
          isNew={taskModal.isNew}
        />
      )}

      {profileModal.open && (
        <ProfileModal
          profile={profileModal.profile}
          onSave={profileModal.isNew ? createProfile : updateProfile}
          onClose={() => setProfileModal({ open: false, profile: null, isNew: false })}
          isNew={profileModal.isNew}
        />
      )}

      {historyModal.open && (
        <HistoryModal
          task={historyModal.task}
          history={historyModal.history}
          onClose={() => setHistoryModal({ open: false, task: null, history: [] })}
        />
      )}
    </div>
  );
}
