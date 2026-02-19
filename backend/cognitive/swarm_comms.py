"""
Swarm Communication Bus + Shared Task Log

Gives KNN sub-agents the ability to:
1. Talk to each other in real-time during a search
2. See what every other agent has found so far
3. React to each other's discoveries (Agent B found X → Agent A searches X deeper)
4. See the full history of what's been searched/uploaded/discovered (no wasted work)

Architecture:
┌─────────────────────────────────────────────────────────┐
│                    SWARM COMM BUS                        │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │              SHARED DISCOVERY FEED                │    │
│  │  Real-time stream of what every agent is finding  │    │
│  │  Any agent can read + react to any other agent   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │              SHARED TASK LOG                      │    │
│  │  Complete history of every search, upload, ingest │    │
│  │  Agents check before searching (no duplicate work)│    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │              REACTIVE TRIGGERS                    │    │
│  │  "Agent B found X" → triggers Agent A to search X │    │
│  │  Cross-pollination between agents in real-time    │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
"""

import logging
import threading
import hashlib
import time
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from queue import Queue, Empty

logger = logging.getLogger(__name__)


@dataclass
class SwarmMessage:
    """A message on the swarm communication bus."""
    sender: str
    message_type: str  # discovery, request, reaction, status
    topic: str
    content: str = ""
    trust_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskLogEntry:
    """A record in the shared task log."""
    task_type: str  # search, upload, ingest, expand, discover
    topic: str
    agent: str
    status: str  # completed, failed, skipped, in_progress
    result_count: int = 0
    trust_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


class SwarmCommBus:
    """
    Real-time communication bus for KNN sub-agents.

    Agents post discoveries here. Other agents read them and react.
    Thread-safe via locks and queues.
    """

    def __init__(self, max_feed_size: int = 500):
        self._feed: deque = deque(maxlen=max_feed_size)
        self._reactive_queues: Dict[str, Queue] = {}
        self._lock = threading.Lock()
        self._listeners: Dict[str, List[Callable]] = {}

    def post(self, message: SwarmMessage):
        """Post a message to the bus. All agents can see it."""
        with self._lock:
            self._feed.append(message)

        # Notify reactive listeners
        for agent_name, callbacks in self._listeners.items():
            if agent_name != message.sender:
                for cb in callbacks:
                    try:
                        cb(message)
                    except Exception:
                        pass

        # Put in reactive queues for agents that poll
        for agent_name, q in self._reactive_queues.items():
            if agent_name != message.sender:
                try:
                    q.put_nowait(message)
                except Exception:
                    pass

    def get_recent(self, limit: int = 20) -> List[SwarmMessage]:
        """Get recent messages from the feed."""
        with self._lock:
            return list(self._feed)[-limit:]

    def get_discoveries_by(self, sender: str) -> List[SwarmMessage]:
        """Get all discoveries by a specific agent."""
        with self._lock:
            return [m for m in self._feed if m.sender == sender and m.message_type == "discovery"]

    def get_all_topics_found(self) -> Set[str]:
        """Get all topics that any agent has found so far."""
        with self._lock:
            return {m.topic for m in self._feed if m.message_type == "discovery"}

    def register_reactive_listener(self, agent_name: str, callback: Callable):
        """Register a callback that fires when another agent posts."""
        if agent_name not in self._listeners:
            self._listeners[agent_name] = []
        self._listeners[agent_name].append(callback)

    def register_reactive_queue(self, agent_name: str) -> Queue:
        """Register a queue for polling reactive messages."""
        q = Queue(maxsize=100)
        self._reactive_queues[agent_name] = q
        return q

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            senders = {}
            for m in self._feed:
                senders[m.sender] = senders.get(m.sender, 0) + 1
            return {
                "total_messages": len(self._feed),
                "messages_by_agent": senders,
                "listeners": list(self._listeners.keys()),
                "reactive_queues": list(self._reactive_queues.keys()),
            }


class SharedTaskLog:
    """
    Complete history of every search, upload, ingest, and discovery.

    Before any agent searches for X, it checks the log:
    - Was X already searched? Skip.
    - Was X already uploaded? Use existing data.
    - Was X already expanded? Don't re-expand.

    This prevents all duplicate work across the entire system.
    """

    def __init__(self, max_entries: int = 10000):
        self._entries: deque = deque(maxlen=max_entries)
        self._topic_index: Dict[str, List[TaskLogEntry]] = {}
        self._completed_topics: Set[str] = set()
        self._lock = threading.Lock()

    def log_task(self, entry: TaskLogEntry):
        """Log a task."""
        with self._lock:
            self._entries.append(entry)
            topic_key = entry.topic.lower().strip()
            if topic_key not in self._topic_index:
                self._topic_index[topic_key] = []
            self._topic_index[topic_key].append(entry)
            if entry.status == "completed":
                self._completed_topics.add(topic_key)

    def was_already_done(self, topic: str, task_type: str = None) -> bool:
        """Check if this topic was already processed."""
        topic_key = topic.lower().strip()
        with self._lock:
            if topic_key in self._completed_topics:
                if task_type:
                    entries = self._topic_index.get(topic_key, [])
                    return any(e.task_type == task_type and e.status == "completed" for e in entries)
                return True
        return False

    def get_history_for(self, topic: str) -> List[TaskLogEntry]:
        """Get all task history for a topic."""
        topic_key = topic.lower().strip()
        with self._lock:
            return list(self._topic_index.get(topic_key, []))

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent task log entries."""
        with self._lock:
            return [
                {
                    "task_type": e.task_type,
                    "topic": e.topic,
                    "agent": e.agent,
                    "status": e.status,
                    "result_count": e.result_count,
                    "trust": e.trust_score,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in list(self._entries)[-limit:]
            ]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            by_type = {}
            by_agent = {}
            by_status = {}
            for e in self._entries:
                by_type[e.task_type] = by_type.get(e.task_type, 0) + 1
                by_agent[e.agent] = by_agent.get(e.agent, 0) + 1
                by_status[e.status] = by_status.get(e.status, 0) + 1
            return {
                "total_entries": len(self._entries),
                "unique_topics": len(self._completed_topics),
                "by_type": by_type,
                "by_agent": by_agent,
                "by_status": by_status,
            }


# Singletons
_comm_bus: Optional[SwarmCommBus] = None
_task_log: Optional[SharedTaskLog] = None


def get_swarm_comm_bus() -> SwarmCommBus:
    global _comm_bus
    if _comm_bus is None:
        _comm_bus = SwarmCommBus()
    return _comm_bus


def get_shared_task_log() -> SharedTaskLog:
    global _task_log
    if _task_log is None:
        _task_log = SharedTaskLog()
    return _task_log
