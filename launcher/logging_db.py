"""
Launcher Logging Database
=========================
Stores launcher and backend logs in SQLite with genesis keys.

Dumb by design: just stores logs, no analysis, no business logic.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class LauncherLogger:
    """
    Logs launcher and backend output to SQLite database.
    
    Minimal implementation: just stores logs with genesis keys and timestamps.
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize launcher logger.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize launcher_log table if it doesn't exist."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS launcher_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        genesis_key TEXT,
                        source TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_launcher_log_timestamp 
                    ON launcher_log(timestamp)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_launcher_log_genesis_key 
                    ON launcher_log(genesis_key)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_launcher_log_level 
                    ON launcher_log(level)
                """)
                conn.commit()
            finally:
                conn.close()
    
    def _parse_level(self, line: str) -> str:
        """
        Parse log level from log line.
        
        Args:
            line: Log line text
            
        Returns:
            Level string: "info", "warning", or "error"
        """
        line_lower = line.lower().strip()
        
        # Check for error indicators
        if any(indicator in line_lower for indicator in [
            "error", "exception", "traceback", "failed", "fatal",
            "[error]", "[err]", "❌"
        ]):
            return "error"
        
        # Check for warning indicators
        if any(indicator in line_lower for indicator in [
            "warn", "warning", "[warn]", "[warning]", "⚠"
        ]):
            return "warning"
        
        # Default to info
        return "info"
    
    def _extract_genesis_key(self, line: str) -> Optional[str]:
        """
        Extract genesis key from log line if present.
        
        Genesis keys typically follow patterns like:
        - GENESIS-XXXX-XXXX
        - GK-XXXX
        - genesis_key: XXX
        
        Args:
            line: Log line text
            
        Returns:
            Genesis key string if found, None otherwise
        """
        import re
        
        # Look for genesis key patterns
        patterns = [
            r'GENESIS-[\w-]+',
            r'GK-[\w-]+',
            r'genesis_key["\']?\s*:\s*([\w-]+)',
            r'genesis["\']?\s*:\s*([\w-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def log(
        self,
        message: str,
        level: Optional[str] = None,
        genesis_key: Optional[str] = None,
        source: Optional[str] = None
    ):
        """
        Log a message to the database.
        
        Args:
            message: Log message text
            level: Log level (info, warning, error) - auto-detected if None
            genesis_key: Genesis key if applicable (auto-extracted if None)
            source: Source of log (e.g., "launcher", "backend", "frontend")
        """
        # Parse level if not provided
        if level is None:
            level = self._parse_level(message)
        
        # Extract genesis key if not provided
        if genesis_key is None:
            genesis_key = self._extract_genesis_key(message)
        
        # Get timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # Insert into database
        with self._lock:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            try:
                conn.execute("""
                    INSERT INTO launcher_log 
                    (timestamp, level, message, genesis_key, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (timestamp, level, message, genesis_key, source))
                conn.commit()
            except Exception as e:
                # Silently fail - don't break launcher if logging fails
                logger.debug(f"Failed to log to database: {e}")
            finally:
                conn.close()
    
    def get_recent_logs(
        self,
        limit: int = 100,
        level: Optional[str] = None,
        genesis_key: Optional[str] = None
    ) -> list:
        """
        Get recent log entries.
        
        Args:
            limit: Maximum number of logs to return
            level: Filter by level (optional)
            genesis_key: Filter by genesis key (optional)
            
        Returns:
            List of log entries as dicts
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                query = "SELECT * FROM launcher_log WHERE 1=1"
                params = []
                
                if level:
                    query += " AND level = ?"
                    params.append(level)
                
                if genesis_key:
                    query += " AND genesis_key = ?"
                    params.append(genesis_key)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
