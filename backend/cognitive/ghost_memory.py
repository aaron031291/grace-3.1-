"""
Ghost Memory — Silent real-time cache alongside every conversation.

Holds EVERYTHING silently. Resets when task is done.
Before reset, captures reflection for the playbook.

Three layers:
  1. Ghost Cache (RAM) — full context of current task
  2. Self-Mirror — reflection before reset
  3. Playbook — long-term evolving knowledge
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PLAYBOOK_DIR = Path(__file__).parent.parent / "data" / "ghost_playbook"


class GhostMemory:
    """Silent real-time cache that sits beside every conversation."""

    _instance = None

    def __init__(self):
        self._cache: List[Dict] = []
        self._task_id: str = ""
        self._task_start: float = 0
        self._error_free_turns: int = 0
        self._total_turns: int = 0

    @classmethod
    def get_instance(cls) -> "GhostMemory":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_task(self, task_description: str):
        """Begin tracking a new task."""
        self._cache = []
        self._task_id = f"ghost_{int(time.time())}"
        self._task_start = time.time()
        self._error_free_turns = 0
        self._total_turns = 0
        self.append("task_start", task_description)

    def append(self, event_type: str, content: str, metadata: Dict = None):
        """Silently append to the ghost cache."""
        self._cache.append({
            "type": event_type,
            "content": content[:3000],
            "metadata": metadata or {},
            "ts": datetime.utcnow().isoformat(),
            "turn": self._total_turns,
        })
        self._total_turns += 1

        if event_type in ("error", "failure", "crash"):
            self._error_free_turns = 0
        else:
            self._error_free_turns += 1

        # Keep cache bounded
        if len(self._cache) > 200:
            self._cache = self._cache[-100:]

    def get_context(self, max_tokens: int = 2000) -> str:
        """Get relevant context for the LLM — silently injected."""
        if not self._cache:
            return ""

        # Build context from most recent entries
        parts = []
        token_count = 0
        for entry in reversed(self._cache):
            line = f"[{entry['type']}] {entry['content'][:200]}"
            est_tokens = len(line) // 4
            if token_count + est_tokens > max_tokens:
                break
            parts.insert(0, line)
            token_count += est_tokens

        return "\n".join(parts)

    def is_task_done(self) -> bool:
        """Check if the current task appears complete."""
        return self._error_free_turns >= 6 and self._total_turns >= 3

    def complete_task(self, user_approved: bool = False) -> Dict[str, Any]:
        """
        Task is done. Reflect, save to playbook, reset cache.
        Returns the reflection.
        """
        if not self._cache:
            return {"status": "no_task"}

        # Self-Mirror reflection
        reflection = self._reflect()

        # Save to playbook
        self._save_to_playbook(reflection)

        # Track via Genesis
        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Ghost memory task completed: {reflection.get('pattern_name', 'unknown')}",
                how="ghost_memory.complete_task",
                output_data=reflection,
                tags=["ghost_memory", "playbook", "reflection"],
            )
        except Exception:
            pass

        # Reset
        result = {"reflection": reflection, "turns": self._total_turns,
                  "duration_s": round(time.time() - self._task_start, 1)}
        self._cache = []
        self._task_id = ""
        self._error_free_turns = 0
        self._total_turns = 0

        return result

    def _reflect(self) -> Dict[str, Any]:
        """Self-mirror: Grace reflects on what happened."""
        errors = [e for e in self._cache if e["type"] in ("error", "failure")]
        successes = [e for e in self._cache if e["type"] in ("success", "pass", "code_generated")]
        code_entries = [e for e in self._cache if e["type"] in ("code", "code_generated")]

        # Determine pattern
        if len(errors) == 0:
            pattern = "clean_success"
            confidence = 0.9
        elif len(successes) > len(errors):
            pattern = "recovered_success"
            confidence = 0.7
        else:
            pattern = "struggled_success"
            confidence = 0.5

        task_desc = self._cache[0]["content"] if self._cache else "unknown"

        return {
            "task_id": self._task_id,
            "pattern_name": pattern,
            "task": task_desc[:200],
            "what_worked": successes[-1]["content"][:200] if successes else "unknown",
            "errors_encountered": len(errors),
            "total_turns": self._total_turns,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_s": round(time.time() - self._task_start, 1),
            "would_do_differently": "Try fewer iterations" if len(errors) > 3 else "Same approach",
        }

    def _save_to_playbook(self, reflection: Dict):
        """Save reflection to the long-term playbook."""
        PLAYBOOK_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        (PLAYBOOK_DIR / f"{reflection['pattern_name']}_{ts}.json").write_text(
            json.dumps(reflection, indent=2, default=str)
        )

        # Store in unified memory
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_procedure(
                name=f"ghost_{reflection['pattern_name']}",
                goal=reflection["task"][:200],
                steps=json.dumps(reflection, default=str),
                trust=reflection["confidence"],
                proc_type="ghost_playbook",
            )
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_task": bool(self._task_id),
            "cache_size": len(self._cache),
            "total_turns": self._total_turns,
            "error_free_turns": self._error_free_turns,
            "task_done": self.is_task_done(),
        }

    def evolve_playbook(self) -> Dict[str, Any]:
        """Nightly: merge similar patterns, boost successful ones."""
        PLAYBOOK_DIR.mkdir(parents=True, exist_ok=True)
        patterns = {}
        for f in PLAYBOOK_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                name = data.get("pattern_name", "unknown")
                if name not in patterns:
                    patterns[name] = []
                patterns[name].append(data)
            except Exception:
                pass

        merged = 0
        for name, entries in patterns.items():
            if len(entries) >= 3:
                # Merge: keep highest confidence, average the rest
                best = max(entries, key=lambda x: x.get("confidence", 0))
                best["merged_count"] = len(entries)
                best["avg_confidence"] = sum(e.get("confidence", 0) for e in entries) / len(entries)
                # Remove old, write merged
                for f in PLAYBOOK_DIR.glob(f"{name}_*.json"):
                    f.unlink()
                (PLAYBOOK_DIR / f"{name}_merged.json").write_text(
                    json.dumps(best, indent=2, default=str)
                )
                merged += 1

        return {"patterns_total": len(patterns), "merged": merged}


def get_ghost_memory() -> GhostMemory:
    return GhostMemory.get_instance()
