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
from datetime import datetime, timezone
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
            "ts": datetime.now(timezone.utc).isoformat(),
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

    def complete_task(self, user_approved: bool = True) -> Dict[str, Any]:
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

        # ── Wire: Ghost Memory → Prompt Builder (reflection for RAG injection) ──
        try:
            from cognitive.event_bus import publish
            lessons = [e for e in self._cache if e["type"] in ("success", "pass", "code_generated", "error", "failure")]
            publish("ghost.reflection_captured", {
                "reflection_id": reflection.get("task_id", ""),
                "summary": reflection.get("task", "")[:500],
                "lessons_count": len(lessons),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, source="ghost_memory")
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_s": round(time.time() - self._task_start, 1),
            "would_do_differently": "Try fewer iterations" if len(errors) > 3 else "Same approach",
        }

    def _save_to_playbook(self, reflection: Dict):
        """Save reflection to the long-term playbook."""
        PLAYBOOK_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
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

    def gm_query(self, subject: str, time_window_hours: float = 24.0,
                 epsilon: float = 0.3) -> List[Dict]:
        """
        GM-Query(subj, t, ε) — retrieve ghost events matching a subject.

        Searches both live RAM cache and persisted playbook reflections.
        Args:
            subject: search term (case-insensitive substring match)
            time_window_hours: how far back to look
            epsilon: fuzzy match threshold (0=exact, 1=everything)
        """
        from datetime import datetime, timezone, timedelta
        results = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        subj_lower = subject.lower()

        # 1. Search live RAM cache
        for entry in reversed(self._cache):
            content = entry.get("content", "").lower()
            event_type = entry.get("type", "").lower()
            # Substring match or type match
            if subj_lower in content or subj_lower in event_type:
                ts_str = entry.get("ts", "")
                if ts_str:
                    try:
                        entry_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if entry_time < cutoff:
                            continue
                    except Exception:
                        pass
                results.append(entry)
            elif epsilon > 0:
                # Fuzzy: check if any word in subject appears in content
                words = subj_lower.split()
                match_ratio = sum(1 for w in words if w in content) / max(len(words), 1)
                if match_ratio >= (1.0 - epsilon):
                    results.append(entry)

        # 2. Search persisted playbook reflections
        if PLAYBOOK_DIR.exists():
            for f in sorted(PLAYBOOK_DIR.glob("*.json"),
                            key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
                try:
                    data = json.loads(f.read_text())
                    task = data.get("task", "").lower()
                    pattern = data.get("pattern_name", "").lower()
                    if subj_lower in task or subj_lower in pattern:
                        ts_str = data.get("timestamp", "")
                        if ts_str:
                            try:
                                entry_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                if entry_time < cutoff:
                                    continue
                            except Exception:
                                pass
                        results.append({
                            "type": "playbook_reflection",
                            "content": data.get("task", "")[:500],
                            "metadata": {
                                "pattern": data.get("pattern_name"),
                                "confidence": data.get("confidence", 0),
                                "errors": data.get("errors_encountered", 0),
                            },
                            "ts": data.get("timestamp", ""),
                            "turn": -1,
                        })
                except Exception:
                    pass

        return results[:50]  # bounded

    def replay_reboot_deltas(self) -> int:
        """
        Replay recent playbook reflections into RAM cache on reboot.
        Restores continuity of self across restarts.
        Returns number of entries replayed.
        """
        if not PLAYBOOK_DIR.exists():
            return 0

        replayed = 0
        # Load the 5 most recent reflections
        recent = sorted(PLAYBOOK_DIR.glob("*.json"),
                        key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        for f in reversed(recent):  # oldest first
            try:
                data = json.loads(f.read_text())
                self.append(
                    "reboot_replay",
                    f"[prior session] {data.get('pattern_name', '?')}: {data.get('task', '')[:200]}",
                    metadata={
                        "replayed_from": f.name,
                        "original_confidence": data.get("confidence", 0),
                        "original_duration": data.get("duration_s", 0),
                    },
                )
                replayed += 1
            except Exception:
                pass

        if replayed:
            logger.info(f"[GHOST] Replayed {replayed} reboot deltas for continuity")
        return replayed

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
