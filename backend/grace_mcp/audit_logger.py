"""
Grace OS — MCP Audit Logger.

Logs every MCP tool call with:
- Timestamp
- Calling layer/context
- Tool name
- Parameters
- Result summary
- Duration
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Immutable audit trail for all MCP tool calls.
    Feeds into the Trust Scorekeeper for confidence tracking.
    """

    def __init__(self, log_dir: str = None):
        if log_dir is None:
            log_dir = str(Path(__file__).parent.parent / "logs" / "mcp_audit")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._entries = []
        self._log_file = self.log_dir / f"mcp_audit_{datetime.now().strftime('%Y%m%d')}.jsonl"

    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        duration_ms: float,
        calling_layer: str = "user",
        session_id: str = None,
        success: bool = True,
        error: str = None
    ):
        """Log a single MCP tool call."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "calling_layer": calling_layer,
            "tool_name": tool_name,
            "arguments": self._sanitize_args(arguments),
            "result_summary": self._summarize_result(result),
            "duration_ms": round(duration_ms, 2),
            "success": success,
            "error": error
        }

        self._entries.append(entry)

        # Write to file
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

        # Log to standard logger
        status = "✅" if success else "❌"
        logger.info(
            f"[MCP AUDIT] {status} {tool_name} "
            f"(layer={calling_layer}, {duration_ms:.0f}ms)"
        )

    def _sanitize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize arguments to avoid logging sensitive/huge data."""
        sanitized = {}
        for key, value in args.items():
            if isinstance(value, str) and len(value) > 500:
                sanitized[key] = value[:500] + f"... ({len(value)} chars total)"
            else:
                sanitized[key] = value
        return sanitized

    def _summarize_result(self, result: Any) -> str:
        """Create a brief summary of the tool result."""
        if result is None:
            return "null"
        result_str = str(result)
        if len(result_str) > 300:
            return result_str[:300] + f"... ({len(result_str)} chars)"
        return result_str

    def get_recent_entries(self, count: int = 50) -> list:
        """Get the most recent audit entries."""
        return self._entries[-count:]

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate stats from audit log."""
        total = len(self._entries)
        successes = sum(1 for e in self._entries if e["success"])
        tool_counts = {}
        for entry in self._entries:
            tool = entry["tool_name"]
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        return {
            "total_calls": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": (successes / total * 100) if total > 0 else 0,
            "tool_counts": tool_counts,
            "log_file": str(self._log_file)
        }
