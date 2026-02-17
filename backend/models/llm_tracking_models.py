"""
LLM Interaction Tracking Models

Database models for tracking every LLM interaction, reasoning path,
extracted pattern, and dependency reduction metrics.

Purpose:
- Record every prompt/response from LLMs (Kimi, coding agents, etc.)
- Capture reasoning chains and decision paths
- Track coding task outcomes (success/failure)
- Store extracted patterns for reducing LLM dependency
- Measure progress toward autonomous operation
"""

from sqlalchemy import (
    Column, String, Text, Float, Boolean, Integer,
    DateTime, JSON, Index, Enum as SQLEnum
)
from database.base import BaseModel
from datetime import datetime
import enum


class InteractionType(str, enum.Enum):
    """Types of LLM interactions."""
    COMMAND_EXECUTION = "command_execution"
    CODING_TASK = "coding_task"
    REASONING = "reasoning"
    PLANNING = "planning"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    QUESTION_ANSWER = "question_answer"
    DELEGATION = "delegation"


class InteractionOutcome(str, enum.Enum):
    """Outcome of an LLM interaction."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    DELEGATED = "delegated"
    PENDING = "pending"


class TaskDelegationType(str, enum.Enum):
    """How a task was delegated."""
    KIMI_DIRECT = "kimi_direct"
    CODING_AGENT = "coding_agent"
    HYBRID = "hybrid"
    GRACE_AUTONOMOUS = "grace_autonomous"


class LLMInteraction(BaseModel):
    """
    Records every LLM interaction for learning and tracking.

    Every time Kimi or any LLM is called, we record:
    - What was asked (prompt)
    - What was returned (response)
    - The reasoning chain used
    - Whether it succeeded or failed
    - How long it took
    - What model was used
    """
    __tablename__ = "llm_interactions"

    interaction_id = Column(String(64), unique=True, nullable=False, index=True)
    session_id = Column(String(64), nullable=True, index=True)

    interaction_type = Column(
        SQLEnum(InteractionType),
        nullable=False,
        default=InteractionType.REASONING
    )
    outcome = Column(
        SQLEnum(InteractionOutcome),
        nullable=False,
        default=InteractionOutcome.PENDING
    )
    delegation_type = Column(
        SQLEnum(TaskDelegationType),
        nullable=True
    )

    model_used = Column(String(128), nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)

    reasoning_chain = Column(JSON, nullable=True)
    decision_path = Column(JSON, nullable=True)
    alternatives_considered = Column(JSON, nullable=True)

    confidence_score = Column(Float, default=0.0)
    trust_score = Column(Float, default=0.5)
    quality_score = Column(Float, nullable=True)

    duration_ms = Column(Float, default=0.0)
    token_count_input = Column(Integer, default=0)
    token_count_output = Column(Integer, default=0)

    error_message = Column(Text, nullable=True)
    error_type = Column(String(128), nullable=True)

    context_used = Column(JSON, nullable=True)
    files_referenced = Column(JSON, nullable=True)
    commands_executed = Column(JSON, nullable=True)

    user_feedback = Column(String(32), nullable=True)
    user_feedback_text = Column(Text, nullable=True)

    genesis_key_id = Column(String(64), nullable=True)
    parent_interaction_id = Column(String(64), nullable=True, index=True)

    metadata_extra = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_llm_interactions_type_outcome", "interaction_type", "outcome"),
        Index("idx_llm_interactions_model", "model_used"),
        Index("idx_llm_interactions_created", "created_at"),
        Index("idx_llm_interactions_session", "session_id"),
    )


class ReasoningPath(BaseModel):
    """
    Captures a complete reasoning path from an LLM interaction.

    A reasoning path is a sequence of steps the LLM took to arrive
    at its answer. By storing these, Grace can learn the patterns
    of successful reasoning and eventually replicate them.
    """
    __tablename__ = "reasoning_paths"

    path_id = Column(String(64), unique=True, nullable=False, index=True)
    interaction_id = Column(String(64), nullable=False, index=True)

    domain = Column(String(128), nullable=True, index=True)
    task_category = Column(String(128), nullable=True, index=True)

    steps = Column(JSON, nullable=False)
    step_count = Column(Integer, default=0)

    entry_conditions = Column(JSON, nullable=True)
    exit_conditions = Column(JSON, nullable=True)

    outcome_success = Column(Boolean, default=False)
    confidence_at_each_step = Column(JSON, nullable=True)

    total_duration_ms = Column(Float, default=0.0)

    pattern_signature = Column(String(256), nullable=True, index=True)
    similarity_hash = Column(String(64), nullable=True, index=True)

    times_seen = Column(Integer, default=1)
    times_succeeded = Column(Integer, default=0)
    times_failed = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    __table_args__ = (
        Index("idx_reasoning_paths_domain", "domain"),
        Index("idx_reasoning_paths_sig", "pattern_signature"),
    )


class ExtractedPattern(BaseModel):
    """
    Patterns extracted from multiple LLM interactions.

    These are higher-level abstractions that represent how the LLM
    solves certain types of problems. By accumulating these, Grace
    can build a deterministic knowledge base that reduces the need
    to call the LLM for known problem types.
    """
    __tablename__ = "extracted_patterns"

    pattern_id = Column(String(64), unique=True, nullable=False, index=True)
    pattern_name = Column(String(256), nullable=False)
    pattern_type = Column(String(64), nullable=False, index=True)

    domain = Column(String(128), nullable=True, index=True)
    task_category = Column(String(128), nullable=True, index=True)

    trigger_conditions = Column(JSON, nullable=False)
    action_sequence = Column(JSON, nullable=False)
    expected_outcomes = Column(JSON, nullable=False)

    confidence_score = Column(Float, default=0.0)
    utility_score = Column(Float, default=0.0)

    times_observed = Column(Integer, default=0)
    times_applied = Column(Integer, default=0)
    times_succeeded = Column(Integer, default=0)
    times_failed = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    supporting_interactions = Column(JSON, nullable=True)
    example_prompts = Column(JSON, nullable=True)
    example_responses = Column(JSON, nullable=True)

    can_replace_llm = Column(Boolean, default=False)
    llm_calls_saved = Column(Integer, default=0)
    estimated_cost_saved = Column(Float, default=0.0)

    last_applied = Column(DateTime, nullable=True)
    last_validated = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_extracted_patterns_type", "pattern_type"),
        Index("idx_extracted_patterns_domain", "domain"),
        Index("idx_extracted_patterns_replaceable", "can_replace_llm"),
    )


class CodingTaskRecord(BaseModel):
    """
    Specific tracking for coding tasks that Kimi delegates to the coding agent.

    Tracks the full lifecycle of a coding task:
    - What was requested
    - How it was delegated
    - What the coding agent did
    - Whether it succeeded
    - What was learned
    """
    __tablename__ = "coding_task_records"

    task_id = Column(String(64), unique=True, nullable=False, index=True)
    interaction_id = Column(String(64), nullable=True, index=True)

    task_description = Column(Text, nullable=False)
    task_type = Column(String(64), nullable=False, index=True)

    delegated_by = Column(String(64), default="kimi")
    delegated_to = Column(String(64), default="coding_agent")

    files_targeted = Column(JSON, nullable=True)
    files_created = Column(JSON, nullable=True)
    files_modified = Column(JSON, nullable=True)

    code_before = Column(JSON, nullable=True)
    code_after = Column(JSON, nullable=True)
    diff_summary = Column(Text, nullable=True)

    tests_run = Column(Boolean, default=False)
    tests_passed = Column(Integer, default=0)
    tests_failed = Column(Integer, default=0)

    outcome = Column(
        SQLEnum(InteractionOutcome),
        nullable=False,
        default=InteractionOutcome.PENDING
    )

    error_message = Column(Text, nullable=True)
    recovery_attempted = Column(Boolean, default=False)
    recovery_successful = Column(Boolean, nullable=True)

    duration_ms = Column(Float, default=0.0)
    iterations = Column(Integer, default=1)

    quality_assessment = Column(JSON, nullable=True)

    reasoning_used = Column(JSON, nullable=True)
    patterns_applied = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_coding_tasks_type_outcome", "task_type", "outcome"),
        Index("idx_coding_tasks_delegated", "delegated_by", "delegated_to"),
    )


class LLMDependencyMetric(BaseModel):
    """
    Tracks LLM dependency reduction over time.

    Measures how much Grace relies on LLMs and tracks progress
    toward handling tasks autonomously using learned patterns.
    """
    __tablename__ = "llm_dependency_metrics"

    metric_id = Column(String(64), unique=True, nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    total_tasks = Column(Integer, default=0)
    tasks_requiring_llm = Column(Integer, default=0)
    tasks_handled_autonomously = Column(Integer, default=0)
    tasks_handled_by_pattern = Column(Integer, default=0)

    llm_dependency_ratio = Column(Float, default=1.0)
    autonomy_ratio = Column(Float, default=0.0)

    domain_breakdown = Column(JSON, nullable=True)
    task_type_breakdown = Column(JSON, nullable=True)

    patterns_available = Column(Integer, default=0)
    patterns_with_high_confidence = Column(Integer, default=0)

    estimated_llm_cost = Column(Float, default=0.0)
    estimated_cost_saved = Column(Float, default=0.0)

    trend_direction = Column(String(16), nullable=True)
    trend_magnitude = Column(Float, default=0.0)

    __table_args__ = (
        Index("idx_dependency_metrics_period", "period_start", "period_end"),
    )
