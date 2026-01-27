/**
 * Grace Planning Tab Component
 *
 * Full planning workflow system with phases:
 * 1. CONCEPT - Big overarching concepts, product, feature
 * 2. QUESTIONS - Non-technical questions about how concepts work
 * 3. TECHNICAL_STACK - Technical discussion about implementation
 * 4. TECHNICAL_ACCEPTANCE - Accept and apply technical decisions
 * 5. EXECUTE - Execute the plan
 * 6. IDE_HANDOFF - Hand off to IDE for implementation
 *
 * @author Grace Autonomous System
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragOverlay,
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    useSortable,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import './GracePlanningTab.css';

import { API_BASE } from '../config/api.js';

// ============================================================================
// CONSTANTS
// ============================================================================

const PLANNING_PHASES = [
    { id: 'concept', label: 'Concept', icon: '💡', description: 'Define the big picture' },
    { id: 'questions', label: 'Questions', icon: '❓', description: 'Clarify requirements' },
    { id: 'technical_stack', label: 'Tech Stack', icon: '🔧', description: 'Choose technologies' },
    { id: 'technical_acceptance', label: 'Decisions', icon: '✅', description: 'Accept technical choices' },
    { id: 'execute', label: 'Execute', icon: '🚀', description: 'Build the plan' },
    { id: 'ide_handoff', label: 'IDE', icon: '💻', description: 'Hand off to IDE' },
];

const CONCEPT_STATUSES = ['draft', 'in_discussion', 'approved', 'rejected', 'archived'];
const QUESTION_TYPES = ['clarification', 'scope', 'functionality', 'user_experience', 'integration', 'constraints'];
const DECISION_STATUSES = ['proposed', 'under_review', 'accepted', 'rejected', 'needs_revision'];

// ============================================================================
// UTILITY COMPONENTS
// ============================================================================

const PhaseIndicator = ({ phases, currentPhase, onPhaseClick, phaseCompletion }) => (
    <div className="phase-indicator">
        {phases.map((phase, index) => {
            const isActive = phase.id === currentPhase;
            const isCompleted = (phaseCompletion[phase.id] || 0) >= 100;
            const isPast = phases.findIndex(p => p.id === currentPhase) > index;

            return (
                <React.Fragment key={phase.id}>
                    <div
                        className={`phase-step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isPast ? 'past' : ''}`}
                        onClick={() => onPhaseClick(phase.id)}
                        title={phase.description}
                    >
                        <div className="phase-icon">{phase.icon}</div>
                        <div className="phase-label">{phase.label}</div>
                        {isCompleted && <div className="phase-check">✓</div>}
                        {!isCompleted && phaseCompletion[phase.id] > 0 && (
                            <div className="phase-progress">{Math.round(phaseCompletion[phase.id])}%</div>
                        )}
                    </div>
                    {index < phases.length - 1 && (
                        <div className={`phase-connector ${isPast || isCompleted ? 'completed' : ''}`} />
                    )}
                </React.Fragment>
            );
        })}
    </div>
);

const GraceThinkingBanner = ({ thinking, isActive }) => (
    <div className={`grace-thinking-banner ${isActive ? 'active' : ''}`}>
        <div className="thinking-indicator-dot" />
        <span className="thinking-label">Grace:</span>
        <span className="thinking-text">{thinking || 'Ready to assist with planning...'}</span>
    </div>
);

// ============================================================================
// SORTABLE CONCEPT CARD
// ============================================================================

const SortableConceptCard = ({ concept, onEdit, onAnalyze, onStatusChange }) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: concept.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.8 : 1,
    };

    const statusColors = {
        draft: '#888',
        in_discussion: '#3b82f6',
        approved: '#22c55e',
        rejected: '#ef4444',
        archived: '#666',
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`concept-card ${isDragging ? 'dragging' : ''}`}
            {...attributes}
            {...listeners}
        >
            <div className="concept-header">
                <h4 className="concept-title">{concept.title}</h4>
                <span
                    className="concept-status"
                    style={{ backgroundColor: `${statusColors[concept.status]}20`, color: statusColors[concept.status] }}
                >
                    {concept.status}
                </span>
            </div>

            <p className="concept-description">{concept.description}</p>

            {concept.vision && (
                <div className="concept-vision">
                    <span className="vision-label">Vision:</span> {concept.vision}
                </div>
            )}

            {concept.goals?.length > 0 && (
                <div className="concept-goals">
                    <span className="goals-label">Goals:</span>
                    <ul>
                        {concept.goals.slice(0, 3).map((goal, i) => (
                            <li key={i}>{goal}</li>
                        ))}
                        {concept.goals.length > 3 && <li>+{concept.goals.length - 3} more</li>}
                    </ul>
                </div>
            )}

            <div className="concept-meta">
                <span className="genesis-id">{concept.genesis_id}</span>
                <span className="priority">P{concept.priority}</span>
                <span className="complexity">{concept.estimated_complexity}</span>
            </div>

            {concept.grace_recommendations?.length > 0 && (
                <div className="grace-recommendations">
                    <span className="rec-label">Grace suggests:</span>
                    <ul>
                        {concept.grace_recommendations.slice(0, 2).map((rec, i) => (
                            <li key={i}>{rec}</li>
                        ))}
                    </ul>
                </div>
            )}

            <div className="concept-actions">
                <button onClick={() => onEdit(concept)} className="action-btn edit">Edit</button>
                <button onClick={() => onAnalyze(concept.id)} className="action-btn analyze">Grace Analyze</button>
                <select
                    value={concept.status}
                    onChange={(e) => onStatusChange(concept.id, e.target.value)}
                    className="status-select"
                >
                    {CONCEPT_STATUSES.map(s => (
                        <option key={s} value={s}>{s.replace('_', ' ')}</option>
                    ))}
                </select>
            </div>
        </div>
    );
};

// ============================================================================
// QUESTION CARD
// ============================================================================

const QuestionCard = ({ question, onAnswer, onResolve }) => {
    const [answerText, setAnswerText] = useState('');
    const [showAnswerForm, setShowAnswerForm] = useState(false);

    const typeColors = {
        clarification: '#3b82f6',
        scope: '#7c3aed',
        functionality: '#22c55e',
        user_experience: '#f59e0b',
        integration: '#00d4ff',
        constraints: '#ef4444',
    };

    const handleSubmitAnswer = () => {
        if (answerText.trim()) {
            onAnswer(question.id, answerText);
            setAnswerText('');
            setShowAnswerForm(false);
        }
    };

    return (
        <div className={`question-card ${question.is_resolved ? 'resolved' : ''}`}>
            <div className="question-header">
                <span
                    className="question-type"
                    style={{ backgroundColor: `${typeColors[question.question_type]}20`, color: typeColors[question.question_type] }}
                >
                    {question.question_type}
                </span>
                {question.is_resolved && <span className="resolved-badge">✓ Resolved</span>}
            </div>

            <p className="question-text">{question.question}</p>

            {question.context && (
                <div className="question-context">
                    <span className="context-label">Context:</span> {question.context}
                </div>
            )}

            {question.grace_suggested_answer && (
                <div className="grace-suggestion">
                    <div className="suggestion-header">
                        <span className="grace-icon">🤖</span>
                        <span>Grace suggests</span>
                        <span className="confidence">{Math.round(question.grace_confidence * 100)}% confidence</span>
                    </div>
                    <p>{question.grace_suggested_answer}</p>
                </div>
            )}

            {question.answers?.length > 0 && (
                <div className="answers-list">
                    <h5>Answers ({question.answers.length})</h5>
                    {question.answers.map((answer, i) => (
                        <div
                            key={answer.id || i}
                            className={`answer ${answer.id === question.accepted_answer ? 'accepted' : ''}`}
                        >
                            <div className="answer-header">
                                <span className="answer-author">{answer.author}</span>
                                {answer.id === question.accepted_answer && (
                                    <span className="accepted-badge">✓ Accepted</span>
                                )}
                            </div>
                            <p>{answer.content}</p>
                        </div>
                    ))}
                </div>
            )}

            <div className="question-actions">
                {!showAnswerForm ? (
                    <>
                        <button onClick={() => setShowAnswerForm(true)} className="action-btn answer">
                            Add Answer
                        </button>
                        {!question.is_resolved && (
                            <button onClick={() => onResolve(question.id)} className="action-btn resolve">
                                Mark Resolved
                            </button>
                        )}
                    </>
                ) : (
                    <div className="answer-form">
                        <textarea
                            value={answerText}
                            onChange={(e) => setAnswerText(e.target.value)}
                            placeholder="Enter your answer..."
                            rows={3}
                        />
                        <div className="form-actions">
                            <button onClick={handleSubmitAnswer} className="action-btn submit">Submit</button>
                            <button onClick={() => setShowAnswerForm(false)} className="action-btn cancel">Cancel</button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

// ============================================================================
// TECH STACK ITEM
// ============================================================================

const TechStackItem = ({ item, onStatusChange }) => {
    const categoryColors = {
        frontend: '#3b82f6',
        backend: '#22c55e',
        database: '#f59e0b',
        infrastructure: '#7c3aed',
        devops: '#00d4ff',
        testing: '#ef4444',
    };

    return (
        <div className={`tech-stack-item ${item.status}`}>
            <div className="tech-header">
                <span
                    className="tech-category"
                    style={{ backgroundColor: `${categoryColors[item.category] || '#888'}20`, color: categoryColors[item.category] || '#888' }}
                >
                    {item.category}
                </span>
                <span className={`tech-status ${item.status}`}>{item.status}</span>
            </div>

            <h4 className="tech-name">{item.name} {item.version && <span className="version">v{item.version}</span>}</h4>
            <p className="tech-purpose">{item.purpose}</p>

            {item.pros?.length > 0 && (
                <div className="tech-pros">
                    <span className="label">Pros:</span>
                    <ul>
                        {item.pros.map((pro, i) => <li key={i}>{pro}</li>)}
                    </ul>
                </div>
            )}

            {item.cons?.length > 0 && (
                <div className="tech-cons">
                    <span className="label">Cons:</span>
                    <ul>
                        {item.cons.map((con, i) => <li key={i}>{con}</li>)}
                    </ul>
                </div>
            )}

            {item.grace_recommendation && (
                <div className="grace-rec">
                    <span className="grace-icon">🤖</span>
                    {item.grace_recommendation}
                </div>
            )}

            <div className="tech-actions">
                <select
                    value={item.status}
                    onChange={(e) => onStatusChange(item.id, e.target.value)}
                    className="status-select"
                >
                    {DECISION_STATUSES.map(s => (
                        <option key={s} value={s}>{s.replace('_', ' ')}</option>
                    ))}
                </select>
            </div>
        </div>
    );
};

// ============================================================================
// TECHNICAL DECISION CARD
// ============================================================================

const TechnicalDecisionCard = ({ decision, onSelect }) => {
    const [selectedOption, setSelectedOption] = useState(decision.selected_option || '');
    const [rationale, setRationale] = useState(decision.rationale || '');

    const handleSelect = () => {
        if (selectedOption && rationale) {
            onSelect(decision.id, selectedOption, rationale);
        }
    };

    return (
        <div className={`decision-card ${decision.status}`}>
            <div className="decision-header">
                <h4>{decision.title}</h4>
                <span className={`decision-status ${decision.status}`}>{decision.status}</span>
            </div>

            <p className="decision-description">{decision.description}</p>
            <span className="decision-type">{decision.decision_type}</span>

            {decision.options?.length > 0 && (
                <div className="decision-options">
                    <h5>Options</h5>
                    {decision.options.map((opt, i) => (
                        <div
                            key={i}
                            className={`option ${selectedOption === opt.name ? 'selected' : ''}`}
                            onClick={() => setSelectedOption(opt.name)}
                        >
                            <div className="option-header">
                                <input
                                    type="radio"
                                    checked={selectedOption === opt.name}
                                    onChange={() => setSelectedOption(opt.name)}
                                />
                                <span className="option-name">{opt.name}</span>
                            </div>
                            <p className="option-desc">{opt.description}</p>
                            {opt.pros && (
                                <div className="option-pros">
                                    <span>Pros:</span> {opt.pros.join(', ')}
                                </div>
                            )}
                            {opt.cons && (
                                <div className="option-cons">
                                    <span>Cons:</span> {opt.cons.join(', ')}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {decision.grace_analysis?.grace_recommendation && (
                <div className="grace-analysis">
                    <span className="grace-icon">🤖</span>
                    <span>Grace recommends:</span> {decision.grace_analysis.grace_recommendation}
                    <p className="reason">{decision.grace_analysis.recommendation_reason}</p>
                </div>
            )}

            {decision.status !== 'accepted' && (
                <div className="decision-form">
                    <textarea
                        value={rationale}
                        onChange={(e) => setRationale(e.target.value)}
                        placeholder="Enter rationale for your decision..."
                        rows={2}
                    />
                    <button
                        onClick={handleSelect}
                        disabled={!selectedOption || !rationale}
                        className="action-btn accept"
                    >
                        Accept Decision
                    </button>
                </div>
            )}

            {decision.status === 'accepted' && (
                <div className="accepted-decision">
                    <h5>Selected: {decision.selected_option}</h5>
                    <p className="rationale"><strong>Rationale:</strong> {decision.rationale}</p>
                </div>
            )}
        </div>
    );
};

// ============================================================================
// EXECUTION PLAN VIEW
// ============================================================================

const ExecutionPlanView = ({ plan, onStart, onUpdateProgress, onGenerateTasks }) => {
    const statusColors = {
        not_started: '#888',
        in_progress: '#3b82f6',
        blocked: '#ef4444',
        completed: '#22c55e',
        failed: '#ef4444',
    };

    return (
        <div className={`execution-plan ${plan.status}`}>
            <div className="plan-header">
                <h3>{plan.title}</h3>
                <span
                    className="plan-status"
                    style={{ backgroundColor: `${statusColors[plan.status]}20`, color: statusColors[plan.status] }}
                >
                    {plan.status}
                </span>
            </div>

            <p className="plan-description">{plan.description}</p>

            <div className="plan-progress">
                <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${plan.progress}%` }} />
                </div>
                <span className="progress-text">{Math.round(plan.progress)}% Complete</span>
            </div>

            {plan.current_phase && (
                <div className="current-phase">
                    <span className="label">Current Phase:</span> {plan.current_phase}
                </div>
            )}

            {plan.phases?.length > 0 && (
                <div className="plan-phases">
                    <h4>Phases</h4>
                    <ol>
                        {plan.phases.map((phase, i) => (
                            <li key={i} className={plan.current_phase === phase.name ? 'current' : ''}>
                                <span className="phase-name">{phase.name}</span>
                                <span className="phase-desc">{phase.description}</span>
                            </li>
                        ))}
                    </ol>
                </div>
            )}

            {plan.milestones?.length > 0 && (
                <div className="plan-milestones">
                    <h4>Milestones</h4>
                    {plan.milestones.map((ms, i) => (
                        <div key={i} className="milestone">
                            <span className="milestone-name">{ms.name}</span>
                            <span className="milestone-criteria">{ms.criteria}</span>
                        </div>
                    ))}
                </div>
            )}

            {plan.tasks?.length > 0 && (
                <div className="plan-tasks">
                    <h4>Generated Tasks ({plan.tasks.length})</h4>
                    {plan.tasks.slice(0, 5).map((task, i) => (
                        <div key={i} className="task-preview">
                            <span className="task-id">{task.id}</span>
                            <span className="task-title">{task.title}</span>
                            <span className={`task-status ${task.status}`}>{task.status}</span>
                        </div>
                    ))}
                    {plan.tasks.length > 5 && <p>+{plan.tasks.length - 5} more tasks</p>}
                </div>
            )}

            <div className="plan-actions">
                {plan.status === 'not_started' && (
                    <button onClick={() => onStart(plan.id)} className="action-btn start">
                        Start Execution
                    </button>
                )}
                {plan.tasks?.length === 0 && (
                    <button onClick={() => onGenerateTasks(plan.id)} className="action-btn generate">
                        Generate Tasks
                    </button>
                )}
                {plan.status === 'in_progress' && (
                    <button onClick={() => onUpdateProgress(plan.id, plan.progress + 10)} className="action-btn progress">
                        Update Progress
                    </button>
                )}
            </div>
        </div>
    );
};

// ============================================================================
// IDE HANDOFF VIEW
// ============================================================================

const IDEHandoffView = ({ handoff, onSend }) => {
    return (
        <div className={`ide-handoff ${handoff.handoff_status}`}>
            <div className="handoff-header">
                <h3>IDE Handoff</h3>
                <span className={`handoff-status ${handoff.handoff_status}`}>{handoff.handoff_status}</span>
            </div>

            <div className="handoff-target">
                <span className="label">Target IDE:</span>
                <span className="value">{handoff.target_ide}</span>
            </div>

            {handoff.target_workspace && (
                <div className="handoff-workspace">
                    <span className="label">Workspace:</span>
                    <span className="value">{handoff.target_workspace}</span>
                </div>
            )}

            {handoff.files_to_create?.length > 0 && (
                <div className="files-section">
                    <h4>Files to Create ({handoff.files_to_create.length})</h4>
                    {handoff.files_to_create.map((file, i) => (
                        <div key={i} className="file-item create">
                            <span className="file-icon">➕</span>
                            <span className="file-path">{file.path}</span>
                            <span className="file-desc">{file.description}</span>
                        </div>
                    ))}
                </div>
            )}

            {handoff.files_to_modify?.length > 0 && (
                <div className="files-section">
                    <h4>Files to Modify ({handoff.files_to_modify.length})</h4>
                    {handoff.files_to_modify.map((file, i) => (
                        <div key={i} className="file-item modify">
                            <span className="file-icon">✏️</span>
                            <span className="file-path">{file.path}</span>
                            <span className="file-changes">{file.changes}</span>
                        </div>
                    ))}
                </div>
            )}

            {handoff.implementation_notes && (
                <div className="impl-notes">
                    <h4>Implementation Notes</h4>
                    <p>{handoff.implementation_notes}</p>
                </div>
            )}

            {handoff.grace_instructions && (
                <div className="grace-instructions">
                    <h4>Grace Instructions</h4>
                    <pre>{handoff.grace_instructions}</pre>
                </div>
            )}

            {handoff.ide_session_id && (
                <div className="session-info">
                    <span className="label">IDE Session:</span>
                    <span className="session-id">{handoff.ide_session_id}</span>
                </div>
            )}

            <div className="handoff-actions">
                {handoff.handoff_status === 'pending' && (
                    <button onClick={() => onSend(handoff.id)} className="action-btn send">
                        Send to IDE
                    </button>
                )}
                {handoff.autonomous_execution && (
                    <span className="auto-badge">Autonomous Execution Enabled</span>
                )}
            </div>
        </div>
    );
};

// ============================================================================
// MODALS
// ============================================================================

const ConceptModal = ({ isOpen, onClose, onSubmit, concept }) => {
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        vision: '',
        goals: [],
        success_criteria: [],
        priority: 5,
        estimated_complexity: 'medium',
        tags: [],
        ...concept
    });
    const [newGoal, setNewGoal] = useState('');
    const [newCriteria, setNewCriteria] = useState('');

    useEffect(() => {
        if (concept) {
            setFormData({ ...formData, ...concept });
        }
    }, [concept]);

    const handleSubmit = (e) => {
        e.preventDefault();
        onSubmit(formData);
        onClose();
    };

    const addGoal = () => {
        if (newGoal.trim()) {
            setFormData({ ...formData, goals: [...formData.goals, newGoal.trim()] });
            setNewGoal('');
        }
    };

    const addCriteria = () => {
        if (newCriteria.trim()) {
            setFormData({ ...formData, success_criteria: [...formData.success_criteria, newCriteria.trim()] });
            setNewCriteria('');
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content concept-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>{concept ? 'Edit Concept' : 'New Concept'}</h2>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>

                <form onSubmit={handleSubmit} className="modal-body">
                    <div className="form-group">
                        <label>Title *</label>
                        <input
                            type="text"
                            value={formData.title}
                            onChange={e => setFormData({ ...formData, title: e.target.value })}
                            required
                            placeholder="Enter concept title..."
                        />
                    </div>

                    <div className="form-group">
                        <label>Description *</label>
                        <textarea
                            value={formData.description}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                            required
                            rows={3}
                            placeholder="Describe the concept..."
                        />
                    </div>

                    <div className="form-group">
                        <label>Vision</label>
                        <textarea
                            value={formData.vision}
                            onChange={e => setFormData({ ...formData, vision: e.target.value })}
                            rows={2}
                            placeholder="Long-term vision for this concept..."
                        />
                    </div>

                    <div className="form-group">
                        <label>Goals</label>
                        <div className="list-input">
                            <input
                                type="text"
                                value={newGoal}
                                onChange={e => setNewGoal(e.target.value)}
                                placeholder="Add a goal..."
                                onKeyPress={e => e.key === 'Enter' && (e.preventDefault(), addGoal())}
                            />
                            <button type="button" onClick={addGoal}>Add</button>
                        </div>
                        <ul className="items-list">
                            {formData.goals.map((g, i) => (
                                <li key={i}>
                                    {g}
                                    <button type="button" onClick={() => setFormData({
                                        ...formData,
                                        goals: formData.goals.filter((_, idx) => idx !== i)
                                    })}>×</button>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className="form-group">
                        <label>Success Criteria</label>
                        <div className="list-input">
                            <input
                                type="text"
                                value={newCriteria}
                                onChange={e => setNewCriteria(e.target.value)}
                                placeholder="Add success criteria..."
                                onKeyPress={e => e.key === 'Enter' && (e.preventDefault(), addCriteria())}
                            />
                            <button type="button" onClick={addCriteria}>Add</button>
                        </div>
                        <ul className="items-list">
                            {formData.success_criteria.map((c, i) => (
                                <li key={i}>
                                    {c}
                                    <button type="button" onClick={() => setFormData({
                                        ...formData,
                                        success_criteria: formData.success_criteria.filter((_, idx) => idx !== i)
                                    })}>×</button>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className="form-row">
                        <div className="form-group">
                            <label>Priority (1-10)</label>
                            <input
                                type="number"
                                min="1"
                                max="10"
                                value={formData.priority}
                                onChange={e => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                            />
                        </div>

                        <div className="form-group">
                            <label>Complexity</label>
                            <select
                                value={formData.estimated_complexity}
                                onChange={e => setFormData({ ...formData, estimated_complexity: e.target.value })}
                            >
                                <option value="low">Low</option>
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                                <option value="very_high">Very High</option>
                            </select>
                        </div>
                    </div>

                    <div className="modal-footer">
                        <button type="button" onClick={onClose} className="btn cancel">Cancel</button>
                        <button type="submit" className="btn submit">
                            {concept ? 'Update Concept' : 'Create Concept'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

const QuestionModal = ({ isOpen, onClose, onSubmit, conceptId }) => {
    const [formData, setFormData] = useState({
        question: '',
        question_type: 'clarification',
        context: '',
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        onSubmit({ ...formData, concept_id: conceptId });
        onClose();
        setFormData({ question: '', question_type: 'clarification', context: '' });
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content question-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>New Question</h2>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>

                <form onSubmit={handleSubmit} className="modal-body">
                    <div className="form-group">
                        <label>Question *</label>
                        <textarea
                            value={formData.question}
                            onChange={e => setFormData({ ...formData, question: e.target.value })}
                            required
                            rows={3}
                            placeholder="What do you need to clarify?"
                        />
                    </div>

                    <div className="form-group">
                        <label>Type</label>
                        <select
                            value={formData.question_type}
                            onChange={e => setFormData({ ...formData, question_type: e.target.value })}
                        >
                            {QUESTION_TYPES.map(t => (
                                <option key={t} value={t}>{t.replace('_', ' ')}</option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label>Context</label>
                        <textarea
                            value={formData.context}
                            onChange={e => setFormData({ ...formData, context: e.target.value })}
                            rows={2}
                            placeholder="Additional context for the question..."
                        />
                    </div>

                    <div className="modal-footer">
                        <button type="button" onClick={onClose} className="btn cancel">Cancel</button>
                        <button type="submit" className="btn submit">Ask Question</button>
                    </div>
                </form>
            </div>
        </div>
    );
};

const TechStackModal = ({ isOpen, onClose, onSubmit, conceptId }) => {
    const [formData, setFormData] = useState({
        category: 'backend',
        name: '',
        version: '',
        purpose: '',
        pros: [],
        cons: [],
    });
    const [newPro, setNewPro] = useState('');
    const [newCon, setNewCon] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        onSubmit({ ...formData, concept_id: conceptId });
        onClose();
        setFormData({ category: 'backend', name: '', version: '', purpose: '', pros: [], cons: [] });
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content tech-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>Add Technology</h2>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>

                <form onSubmit={handleSubmit} className="modal-body">
                    <div className="form-row">
                        <div className="form-group">
                            <label>Category *</label>
                            <select
                                value={formData.category}
                                onChange={e => setFormData({ ...formData, category: e.target.value })}
                            >
                                <option value="frontend">Frontend</option>
                                <option value="backend">Backend</option>
                                <option value="database">Database</option>
                                <option value="infrastructure">Infrastructure</option>
                                <option value="devops">DevOps</option>
                                <option value="testing">Testing</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label>Version</label>
                            <input
                                type="text"
                                value={formData.version}
                                onChange={e => setFormData({ ...formData, version: e.target.value })}
                                placeholder="e.g., 18.0"
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Name *</label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={e => setFormData({ ...formData, name: e.target.value })}
                            required
                            placeholder="e.g., React, PostgreSQL"
                        />
                    </div>

                    <div className="form-group">
                        <label>Purpose *</label>
                        <textarea
                            value={formData.purpose}
                            onChange={e => setFormData({ ...formData, purpose: e.target.value })}
                            required
                            rows={2}
                            placeholder="Why are we using this technology?"
                        />
                    </div>

                    <div className="form-group">
                        <label>Pros</label>
                        <div className="list-input">
                            <input
                                type="text"
                                value={newPro}
                                onChange={e => setNewPro(e.target.value)}
                                placeholder="Add a pro..."
                            />
                            <button type="button" onClick={() => {
                                if (newPro.trim()) {
                                    setFormData({ ...formData, pros: [...formData.pros, newPro.trim()] });
                                    setNewPro('');
                                }
                            }}>Add</button>
                        </div>
                        <ul className="items-list pros">
                            {formData.pros.map((p, i) => (
                                <li key={i}>
                                    {p}
                                    <button type="button" onClick={() => setFormData({
                                        ...formData,
                                        pros: formData.pros.filter((_, idx) => idx !== i)
                                    })}>×</button>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className="form-group">
                        <label>Cons</label>
                        <div className="list-input">
                            <input
                                type="text"
                                value={newCon}
                                onChange={e => setNewCon(e.target.value)}
                                placeholder="Add a con..."
                            />
                            <button type="button" onClick={() => {
                                if (newCon.trim()) {
                                    setFormData({ ...formData, cons: [...formData.cons, newCon.trim()] });
                                    setNewCon('');
                                }
                            }}>Add</button>
                        </div>
                        <ul className="items-list cons">
                            {formData.cons.map((c, i) => (
                                <li key={i}>
                                    {c}
                                    <button type="button" onClick={() => setFormData({
                                        ...formData,
                                        cons: formData.cons.filter((_, idx) => idx !== i)
                                    })}>×</button>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className="modal-footer">
                        <button type="button" onClick={onClose} className="btn cancel">Cancel</button>
                        <button type="submit" className="btn submit">Add Technology</button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const GracePlanningTab = ({ genesisId = 'G-USER-001' }) => {
    // State
    const [session, setSession] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [concepts, setConcepts] = useState([]);
    const [questions, setQuestions] = useState([]);
    const [techStack, setTechStack] = useState([]);
    const [decisions, setDecisions] = useState([]);
    const [executionPlans, setExecutionPlans] = useState([]);
    const [ideHandoffs, setIdeHandoffs] = useState([]);

    const [currentPhase, setCurrentPhase] = useState('concept');
    const [phaseCompletion, setPhaseCompletion] = useState({});
    const [graceThinking, setGraceThinking] = useState('');
    const [isGraceActive, setIsGraceActive] = useState(false);

    const [selectedConcept, setSelectedConcept] = useState(null);
    const [wsConnection, setWsConnection] = useState(null);

    // Modals
    const [showConceptModal, setShowConceptModal] = useState(false);
    const [showQuestionModal, setShowQuestionModal] = useState(false);
    const [showTechModal, setShowTechModal] = useState(false);
    const [editingConcept, setEditingConcept] = useState(null);
    const [showSessionModal, setShowSessionModal] = useState(false);

    // DnD sensors
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // ========================================================================
    // API CALLS
    // ========================================================================

    const fetchSessions = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/grace-planning/sessions?genesis_id=${genesisId}`);
            const data = await res.json();
            setSessions(data);
        } catch (err) {
            console.error('Failed to fetch sessions:', err);
        }
    }, [genesisId]);

    const fetchSessionState = useCallback(async (sessionId) => {
        try {
            const res = await fetch(`${API_BASE}/api/grace-planning/sessions/${sessionId}/full-state`);
            const data = await res.json();

            setSession(data.session);
            setConcepts(data.concepts || []);
            setQuestions(data.questions || []);
            setTechStack(data.tech_stack || []);
            setDecisions(data.decisions || []);
            setExecutionPlans(data.execution_plans || []);
            setIdeHandoffs(data.ide_handoffs || []);
            setCurrentPhase(data.session.current_phase);
            setPhaseCompletion(data.session.phase_completion || {});
        } catch (err) {
            console.error('Failed to fetch session state:', err);
        }
    }, []);

    const createSession = async (title, description) => {
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/sessions?genesis_id=${genesisId}&title=${encodeURIComponent(title)}&description=${encodeURIComponent(description)}`,
                { method: 'POST' }
            );
            const newSession = await res.json();
            setSessions([newSession, ...sessions]);
            setSession(newSession);
            setCurrentPhase(newSession.current_phase);
        } catch (err) {
            console.error('Failed to create session:', err);
        }
    };

    const createConcept = async (conceptData) => {
        if (!session) return;
        try {
            const params = new URLSearchParams({
                session_id: session.id,
                genesis_id: genesisId,
                title: conceptData.title,
                description: conceptData.description,
                vision: conceptData.vision || '',
                priority: conceptData.priority?.toString() || '5',
            });

            const res = await fetch(`${API_BASE}/api/grace-planning/concepts?${params}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    goals: conceptData.goals || [],
                    success_criteria: conceptData.success_criteria || [],
                    tags: conceptData.tags || [],
                }),
            });
            const newConcept = await res.json();
            setConcepts([...concepts, newConcept]);
        } catch (err) {
            console.error('Failed to create concept:', err);
        }
    };

    const analyzeConcept = async (conceptId) => {
        setIsGraceActive(true);
        setGraceThinking('Analyzing concept and generating recommendations...');
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/concepts/${conceptId}/grace-analyze`,
                { method: 'POST' }
            );
            const updated = await res.json();
            setConcepts(concepts.map(c => c.id === conceptId ? updated : c));
            setGraceThinking('Analysis complete. Recommendations generated.');
        } catch (err) {
            console.error('Failed to analyze concept:', err);
            setGraceThinking('Analysis failed. Please try again.');
        } finally {
            setTimeout(() => setIsGraceActive(false), 2000);
        }
    };

    const updateConceptStatus = async (conceptId, status) => {
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/concepts/${conceptId}/status?status=${status}`,
                { method: 'PUT' }
            );
            const updated = await res.json();
            setConcepts(concepts.map(c => c.id === conceptId ? updated : c));
        } catch (err) {
            console.error('Failed to update concept status:', err);
        }
    };

    const createQuestion = async (questionData) => {
        if (!session) return;
        try {
            const params = new URLSearchParams({
                session_id: session.id,
                concept_id: questionData.concept_id,
                genesis_id: genesisId,
                question: questionData.question,
                question_type: questionData.question_type,
                context: questionData.context || '',
            });

            const res = await fetch(`${API_BASE}/api/grace-planning/questions?${params}`, {
                method: 'POST',
            });
            const newQuestion = await res.json();
            setQuestions([...questions, newQuestion]);
        } catch (err) {
            console.error('Failed to create question:', err);
        }
    };

    const answerQuestion = async (questionId, content) => {
        try {
            const params = new URLSearchParams({
                author: genesisId,
                content: content,
            });
            const res = await fetch(
                `${API_BASE}/api/grace-planning/questions/${questionId}/answer?${params}`,
                { method: 'POST' }
            );
            const updated = await res.json();
            setQuestions(questions.map(q => q.id === questionId ? updated : q));
        } catch (err) {
            console.error('Failed to answer question:', err);
        }
    };

    const resolveQuestion = async (questionId) => {
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/questions/${questionId}/resolve`,
                { method: 'POST' }
            );
            const updated = await res.json();
            setQuestions(questions.map(q => q.id === questionId ? updated : q));
        } catch (err) {
            console.error('Failed to resolve question:', err);
        }
    };

    const addTechStackItem = async (itemData) => {
        if (!session) return;
        try {
            const params = new URLSearchParams({
                session_id: session.id,
                concept_id: itemData.concept_id,
                category: itemData.category,
                name: itemData.name,
                purpose: itemData.purpose,
            });
            if (itemData.version) params.append('version', itemData.version);

            const res = await fetch(`${API_BASE}/api/grace-planning/tech-stack?${params}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pros: itemData.pros || [],
                    cons: itemData.cons || [],
                }),
            });
            const newItem = await res.json();
            setTechStack([...techStack, newItem]);
        } catch (err) {
            console.error('Failed to add tech stack item:', err);
        }
    };

    const updateTechStackStatus = async (itemId, status, rationale = '') => {
        try {
            const params = new URLSearchParams({ status });
            if (rationale) params.append('decision_rationale', rationale);

            const res = await fetch(
                `${API_BASE}/api/grace-planning/tech-stack/${itemId}/status?${params}`,
                { method: 'PUT' }
            );
            const updated = await res.json();
            setTechStack(techStack.map(t => t.id === itemId ? updated : t));
        } catch (err) {
            console.error('Failed to update tech stack status:', err);
        }
    };

    const selectDecision = async (decisionId, selectedOption, rationale) => {
        try {
            const params = new URLSearchParams({
                selected_option: selectedOption,
                rationale: rationale,
            });

            const res = await fetch(
                `${API_BASE}/api/grace-planning/decisions/${decisionId}/select?${params}`,
                { method: 'PUT' }
            );
            const updated = await res.json();
            setDecisions(decisions.map(d => d.id === decisionId ? updated : d));
        } catch (err) {
            console.error('Failed to select decision:', err);
        }
    };

    const startExecution = async (planId) => {
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/execution-plans/${planId}/start`,
                { method: 'PUT' }
            );
            const updated = await res.json();
            setExecutionPlans(executionPlans.map(p => p.id === planId ? updated : p));
        } catch (err) {
            console.error('Failed to start execution:', err);
        }
    };

    const updateExecutionProgress = async (planId, progress) => {
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/execution-plans/${planId}/progress?progress=${progress}`,
                { method: 'PUT' }
            );
            const updated = await res.json();
            setExecutionPlans(executionPlans.map(p => p.id === planId ? updated : p));
        } catch (err) {
            console.error('Failed to update progress:', err);
        }
    };

    const generateTasks = async (planId) => {
        setIsGraceActive(true);
        setGraceThinking('Generating tasks from execution plan...');
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/execution-plans/${planId}/generate-tasks`,
                { method: 'POST' }
            );
            const updated = await res.json();
            setExecutionPlans(executionPlans.map(p => p.id === planId ? updated : p));
            setGraceThinking(`Generated ${updated.tasks?.length || 0} tasks successfully.`);
        } catch (err) {
            console.error('Failed to generate tasks:', err);
            setGraceThinking('Task generation failed.');
        } finally {
            setTimeout(() => setIsGraceActive(false), 2000);
        }
    };

    const sendToIDE = async (handoffId) => {
        setIsGraceActive(true);
        setGraceThinking('Sending implementation to IDE...');
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/ide-handoffs/${handoffId}/send`,
                { method: 'POST' }
            );
            const updated = await res.json();
            setIdeHandoffs(ideHandoffs.map(h => h.id === handoffId ? updated : h));
            setGraceThinking(`Sent to IDE. Session: ${updated.ide_session_id}`);
        } catch (err) {
            console.error('Failed to send to IDE:', err);
            setGraceThinking('Failed to send to IDE.');
        } finally {
            setTimeout(() => setIsGraceActive(false), 3000);
        }
    };

    const completePhase = async () => {
        if (!session) return;
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/sessions/${session.id}/complete-phase`,
                { method: 'POST' }
            );
            const result = await res.json();
            if (result.next_phase) {
                setCurrentPhase(result.next_phase);
            }
            setPhaseCompletion({ ...phaseCompletion, [result.completed_phase]: 100 });
        } catch (err) {
            console.error('Failed to complete phase:', err);
        }
    };

    const graceAnalyzeSession = async () => {
        if (!session) return;
        setIsGraceActive(true);
        setGraceThinking('Analyzing entire planning session...');
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/sessions/${session.id}/grace/analyze-all`,
                { method: 'POST' }
            );
            const analysis = await res.json();
            setGraceThinking(
                `Analysis complete. ${analysis.recommendations?.length || 0} recommendations. ` +
                `Next steps: ${analysis.next_steps?.[0] || 'Continue with current phase'}`
            );
        } catch (err) {
            console.error('Failed to analyze session:', err);
            setGraceThinking('Session analysis failed.');
        } finally {
            setTimeout(() => setIsGraceActive(false), 5000);
        }
    };

    const graceGenerateExecutionPlan = async (conceptId) => {
        if (!session) return;
        setIsGraceActive(true);
        setGraceThinking('Generating execution plan from concept...');
        try {
            const res = await fetch(
                `${API_BASE}/api/grace-planning/sessions/${session.id}/grace/generate-execution-plan?concept_id=${conceptId}`,
                { method: 'POST' }
            );
            const plan = await res.json();
            setExecutionPlans([...executionPlans, plan]);
            setGraceThinking(`Created execution plan: ${plan.title}`);
        } catch (err) {
            console.error('Failed to generate execution plan:', err);
            setGraceThinking('Failed to generate execution plan.');
        } finally {
            setTimeout(() => setIsGraceActive(false), 3000);
        }
    };

    // ========================================================================
    // EFFECTS
    // ========================================================================

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    useEffect(() => {
        if (session?.id) {
            // Connect WebSocket
            const ws = new WebSocket(`ws://localhost:8000/api/grace-planning/ws/${session.id}`);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            ws.onerror = (err) => console.error('WebSocket error:', err);
            setWsConnection(ws);

            return () => ws.close();
        }
    }, [session?.id]);

    const handleWebSocketMessage = (data) => {
        switch (data.type) {
            case 'concept_created':
                setConcepts(prev => [...prev, data.concept]);
                break;
            case 'question_created':
                setQuestions(prev => [...prev, data.question]);
                break;
            case 'phase_changed':
                setCurrentPhase(data.phase);
                break;
            default:
                break;
        }
    };

    // ========================================================================
    // DND HANDLERS
    // ========================================================================

    const handleDragEnd = (event) => {
        const { active, over } = event;
        if (active.id !== over?.id) {
            setConcepts((items) => {
                const oldIndex = items.findIndex(i => i.id === active.id);
                const newIndex = items.findIndex(i => i.id === over.id);
                return arrayMove(items, oldIndex, newIndex);
            });
        }
    };

    // ========================================================================
    // RENDER HELPERS
    // ========================================================================

    const renderPhaseContent = () => {
        switch (currentPhase) {
            case 'concept':
                return renderConceptPhase();
            case 'questions':
                return renderQuestionsPhase();
            case 'technical_stack':
                return renderTechStackPhase();
            case 'technical_acceptance':
                return renderDecisionsPhase();
            case 'execute':
                return renderExecutePhase();
            case 'ide_handoff':
                return renderIDEHandoffPhase();
            default:
                return <div className="phase-content">Select a phase to begin</div>;
        }
    };

    const renderConceptPhase = () => (
        <div className="phase-content concept-phase">
            <div className="phase-header">
                <h2>💡 Concepts</h2>
                <p>Define the big picture - what are we building?</p>
                <button onClick={() => setShowConceptModal(true)} className="add-btn">
                    + New Concept
                </button>
            </div>

            <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
            >
                <SortableContext
                    items={concepts.map(c => c.id)}
                    strategy={verticalListSortingStrategy}
                >
                    <div className="concepts-grid">
                        {concepts.map(concept => (
                            <SortableConceptCard
                                key={concept.id}
                                concept={concept}
                                onEdit={(c) => {
                                    setEditingConcept(c);
                                    setShowConceptModal(true);
                                }}
                                onAnalyze={analyzeConcept}
                                onStatusChange={updateConceptStatus}
                            />
                        ))}
                    </div>
                </SortableContext>
            </DndContext>

            {concepts.length === 0 && (
                <div className="empty-state">
                    <span className="empty-icon">💡</span>
                    <p>No concepts yet. Start by adding your first concept!</p>
                </div>
            )}
        </div>
    );

    const renderQuestionsPhase = () => {
        const approvedConcepts = concepts.filter(c => c.status === 'approved');

        return (
            <div className="phase-content questions-phase">
                <div className="phase-header">
                    <h2>❓ Questions</h2>
                    <p>Clarify requirements - what needs to be understood?</p>
                </div>

                {approvedConcepts.length === 0 ? (
                    <div className="empty-state">
                        <span className="empty-icon">⚠️</span>
                        <p>Approve at least one concept before asking questions.</p>
                    </div>
                ) : (
                    <div className="questions-by-concept">
                        {approvedConcepts.map(concept => {
                            const conceptQuestions = questions.filter(q => q.concept_id === concept.id);
                            return (
                                <div key={concept.id} className="concept-questions">
                                    <div className="concept-header-mini">
                                        <h3>{concept.title}</h3>
                                        <button
                                            onClick={() => {
                                                setSelectedConcept(concept);
                                                setShowQuestionModal(true);
                                            }}
                                            className="add-btn small"
                                        >
                                            + Question
                                        </button>
                                    </div>

                                    <div className="questions-list">
                                        {conceptQuestions.map(q => (
                                            <QuestionCard
                                                key={q.id}
                                                question={q}
                                                onAnswer={answerQuestion}
                                                onResolve={resolveQuestion}
                                            />
                                        ))}
                                        {conceptQuestions.length === 0 && (
                                            <p className="no-questions">No questions for this concept yet.</p>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        );
    };

    const renderTechStackPhase = () => {
        const approvedConcepts = concepts.filter(c => c.status === 'approved');
        const categories = [...new Set(techStack.map(t => t.category))];

        return (
            <div className="phase-content tech-stack-phase">
                <div className="phase-header">
                    <h2>🔧 Tech Stack</h2>
                    <p>Choose technologies - what tools will we use?</p>
                </div>

                {approvedConcepts.length === 0 ? (
                    <div className="empty-state">
                        <span className="empty-icon">⚠️</span>
                        <p>Approve at least one concept first.</p>
                    </div>
                ) : (
                    <>
                        <div className="concept-selector">
                            <label>Add technology for:</label>
                            <select
                                onChange={(e) => {
                                    setSelectedConcept(concepts.find(c => c.id === e.target.value));
                                    setShowTechModal(true);
                                }}
                                value=""
                            >
                                <option value="" disabled>Select concept...</option>
                                {approvedConcepts.map(c => (
                                    <option key={c.id} value={c.id}>{c.title}</option>
                                ))}
                            </select>
                        </div>

                        <div className="tech-stack-grid">
                            {categories.map(cat => (
                                <div key={cat} className="category-column">
                                    <h3 className="category-title">{cat}</h3>
                                    {techStack.filter(t => t.category === cat).map(item => (
                                        <TechStackItem
                                            key={item.id}
                                            item={item}
                                            onStatusChange={updateTechStackStatus}
                                        />
                                    ))}
                                </div>
                            ))}
                        </div>

                        {techStack.length === 0 && (
                            <div className="empty-state">
                                <span className="empty-icon">🔧</span>
                                <p>No technologies added yet. Start building your stack!</p>
                            </div>
                        )}
                    </>
                )}
            </div>
        );
    };

    const renderDecisionsPhase = () => (
        <div className="phase-content decisions-phase">
            <div className="phase-header">
                <h2>✅ Technical Decisions</h2>
                <p>Accept and apply technical choices</p>
            </div>

            <div className="decisions-list">
                {decisions.map(decision => (
                    <TechnicalDecisionCard
                        key={decision.id}
                        decision={decision}
                        onSelect={selectDecision}
                    />
                ))}
            </div>

            {decisions.length === 0 && (
                <div className="empty-state">
                    <span className="empty-icon">✅</span>
                    <p>No pending decisions. All tech stack items accepted!</p>
                </div>
            )}
        </div>
    );

    const renderExecutePhase = () => {
        const approvedConcepts = concepts.filter(c => c.status === 'approved');

        return (
            <div className="phase-content execute-phase">
                <div className="phase-header">
                    <h2>🚀 Execute</h2>
                    <p>Build the plan - let's make it happen!</p>
                </div>

                {approvedConcepts.length > 0 && executionPlans.length === 0 && (
                    <div className="generate-plans">
                        <p>Generate execution plans from approved concepts:</p>
                        {approvedConcepts.map(c => (
                            <button
                                key={c.id}
                                onClick={() => graceGenerateExecutionPlan(c.id)}
                                className="generate-btn"
                            >
                                Generate Plan for "{c.title}"
                            </button>
                        ))}
                    </div>
                )}

                <div className="execution-plans-list">
                    {executionPlans.map(plan => (
                        <ExecutionPlanView
                            key={plan.id}
                            plan={plan}
                            onStart={startExecution}
                            onUpdateProgress={updateExecutionProgress}
                            onGenerateTasks={generateTasks}
                        />
                    ))}
                </div>

                {executionPlans.length === 0 && approvedConcepts.length === 0 && (
                    <div className="empty-state">
                        <span className="empty-icon">🚀</span>
                        <p>Approve concepts and create execution plans to begin.</p>
                    </div>
                )}
            </div>
        );
    };

    const renderIDEHandoffPhase = () => (
        <div className="phase-content ide-handoff-phase">
            <div className="phase-header">
                <h2>💻 IDE Handoff</h2>
                <p>Hand off to IDE for implementation</p>
            </div>

            <div className="handoffs-list">
                {ideHandoffs.map(handoff => (
                    <IDEHandoffView
                        key={handoff.id}
                        handoff={handoff}
                        onSend={sendToIDE}
                    />
                ))}
            </div>

            {ideHandoffs.length === 0 && (
                <div className="empty-state">
                    <span className="empty-icon">💻</span>
                    <p>No IDE handoffs created yet. Complete execution plans first.</p>
                </div>
            )}
        </div>
    );

    // ========================================================================
    // MAIN RENDER
    // ========================================================================

    if (!session) {
        return (
            <div className="grace-planning-container">
                <div className="planning-header">
                    <h1>🎯 Grace Planning</h1>
                    <button onClick={() => setShowSessionModal(true)} className="new-session-btn">
                        + New Planning Session
                    </button>
                </div>

                <div className="sessions-list">
                    <h2>Your Planning Sessions</h2>
                    {sessions.map(s => (
                        <div
                            key={s.id}
                            className="session-card"
                            onClick={() => fetchSessionState(s.id)}
                        >
                            <h3>{s.title}</h3>
                            <p>{s.description}</p>
                            <div className="session-meta">
                                <span className="phase">{s.current_phase}</span>
                                <span className="date">{new Date(s.created_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                    ))}
                    {sessions.length === 0 && (
                        <div className="empty-state">
                            <span className="empty-icon">📋</span>
                            <p>No planning sessions yet. Create your first one!</p>
                        </div>
                    )}
                </div>

                {showSessionModal && (
                    <div className="modal-overlay" onClick={() => setShowSessionModal(false)}>
                        <div className="modal-content" onClick={e => e.stopPropagation()}>
                            <h2>New Planning Session</h2>
                            <form onSubmit={(e) => {
                                e.preventDefault();
                                const formData = new FormData(e.target);
                                createSession(formData.get('title'), formData.get('description'));
                                setShowSessionModal(false);
                            }}>
                                <div className="form-group">
                                    <label>Title</label>
                                    <input name="title" required placeholder="e.g., User Authentication System" />
                                </div>
                                <div className="form-group">
                                    <label>Description</label>
                                    <textarea name="description" rows={3} placeholder="Brief description..." />
                                </div>
                                <div className="modal-footer">
                                    <button type="button" onClick={() => setShowSessionModal(false)}>Cancel</button>
                                    <button type="submit" className="primary">Create Session</button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="grace-planning-container">
            <div className="planning-header">
                <div className="header-left">
                    <button onClick={() => setSession(null)} className="back-btn">← Sessions</button>
                    <h1>{session.title}</h1>
                </div>
                <div className="header-actions">
                    <button onClick={graceAnalyzeSession} className="analyze-btn">
                        🤖 Grace Analyze
                    </button>
                    <button onClick={completePhase} className="complete-phase-btn">
                        Complete Phase →
                    </button>
                </div>
            </div>

            <GraceThinkingBanner thinking={graceThinking} isActive={isGraceActive} />

            <PhaseIndicator
                phases={PLANNING_PHASES}
                currentPhase={currentPhase}
                onPhaseClick={setCurrentPhase}
                phaseCompletion={phaseCompletion}
            />

            <div className="planning-content">
                {renderPhaseContent()}
            </div>

            {/* Modals */}
            <ConceptModal
                isOpen={showConceptModal}
                onClose={() => {
                    setShowConceptModal(false);
                    setEditingConcept(null);
                }}
                onSubmit={createConcept}
                concept={editingConcept}
            />

            <QuestionModal
                isOpen={showQuestionModal}
                onClose={() => {
                    setShowQuestionModal(false);
                    setSelectedConcept(null);
                }}
                onSubmit={createQuestion}
                conceptId={selectedConcept?.id}
            />

            <TechStackModal
                isOpen={showTechModal}
                onClose={() => {
                    setShowTechModal(false);
                    setSelectedConcept(null);
                }}
                onSubmit={addTechStackItem}
                conceptId={selectedConcept?.id}
            />
        </div>
    );
};

export default GracePlanningTab;
