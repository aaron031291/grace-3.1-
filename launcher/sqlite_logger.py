"""
SQLite Logger for Grace Launcher
=================================
Captures stdout/stderr and stores each line in SQLite database.
"""

import sqlite3
import re
import sys
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging
import uuid


class SQLiteLogHandler(logging.Handler):
    """
    Custom logging handler that writes to SQLite database.
    """
    
    def __init__(self, db_path: Path, genesis_key: Optional[str] = None):
        super().__init__()
        self.db_path = Path(db_path)
        self.genesis_key = genesis_key or f"GK-LAUNCHER-{uuid.uuid4().hex[:12]}"
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database and create table if needed."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS launcher_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    genesis_key TEXT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Migrate: Add source column if it doesn't exist
            try:
                cursor.execute("SELECT source FROM launcher_log LIMIT 1")
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                cursor.execute("ALTER TABLE launcher_log ADD COLUMN source TEXT")
            
            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_genesis_key 
                ON launcher_log(genesis_key)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON launcher_log(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_level 
                ON launcher_log(level)
            """)
            
            conn.commit()
            conn.close()
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record to SQLite."""
        try:
            # Extract level from record
            level = record.levelname.lower()
            
            # Format message
            message = self.format(record)
            
            # Insert into database
            with self._lock:
                conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO launcher_log (genesis_key, timestamp, level, message, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self.genesis_key,
                    datetime.utcnow().isoformat(),
                    level,
                    message,
                    "launcher"
                ))
                
                conn.commit()
                conn.close()
        except Exception:
            # Don't let logging errors break the launcher
            self.handleError(record)


class LauncherLogCapture:
    """
    Captures stdout/stderr from launcher and subprocesses, storing in SQLite.
    """
    
    def __init__(self, db_path: Path, genesis_key: Optional[str] = None):
        self.db_path = Path(db_path)
        self.genesis_key = genesis_key or f"GK-LAUNCHER-{uuid.uuid4().hex[:12]}"
        self._lock = threading.Lock()
        self._init_db()
        self._running = False
        self._threads = []
    
    def _init_db(self):
        """Initialize SQLite database and create table if needed."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS launcher_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    genesis_key TEXT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Migrate: Add source column if it doesn't exist
            try:
                cursor.execute("SELECT source FROM launcher_log LIMIT 1")
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                cursor.execute("ALTER TABLE launcher_log ADD COLUMN source TEXT")
            
            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_genesis_key 
                ON launcher_log(genesis_key)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON launcher_log(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_level 
                ON launcher_log(level)
            """)
            
            conn.commit()
            conn.close()
    
    def _parse_level(self, line: str) -> str:
        """
        Parse log level from line.
        
        Looks for patterns like:
        - [INFO], [WARNING], [ERROR], [DEBUG]
        - INFO:, WARNING:, ERROR:, DEBUG:
        - Standard Python logging format
        """
        line_upper = line.upper()
        
        if re.search(r'\[ERROR\]|ERROR:', line_upper):
            return 'error'
        elif re.search(r'\[WARNING\]|\[WARN\]|WARNING:|WARN:', line_upper):
            return 'warning'
        elif re.search(r'\[INFO\]|INFO:', line_upper):
            return 'info'
        elif re.search(r'\[DEBUG\]|DEBUG:', line_upper):
            return 'debug'
        elif re.search(r'❌|FAILED|FAIL|ERROR', line_upper):
            return 'error'
        elif re.search(r'⚠|WARNING|WARN', line_upper):
            return 'warning'
        elif re.search(r'✓|SUCCESS|OK', line_upper):
            return 'info'
        else:
            # Default to info if no level detected
            return 'info'
    
    def log_line(self, line: str, level: Optional[str] = None, stream_name: Optional[str] = None):
        """
        Store a log line in the database.
        
        Args:
            line: The log line to store
            level: Optional log level (if None, will be parsed from line)
            stream_name: Optional source stream name (e.g., "backend-stdout", "backend-stderr")
        """
        if not line.strip():
            return
        
        # Parse level if not provided
        if level is None:
            level = self._parse_level(line)
        
        # Extract genesis key from line if present
        genesis_key = self._extract_genesis_key(line)
        
        # Store in database
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO launcher_log (genesis_key, timestamp, level, message, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    genesis_key or self.genesis_key,  # Use extracted key or default
                    datetime.utcnow().isoformat(),
                    level,
                    line.strip(),
                    stream_name or "launcher"
                ))
                
                conn.commit()
                conn.close()
        except Exception as e:
            # Don't let logging errors break the launcher
            print(f"Error storing log line: {e}", file=sys.stderr)
    
    def _extract_genesis_key(self, line: str) -> Optional[str]:
        """
        Extract genesis key from log line if present.
        
        Args:
            line: Log line text
            
        Returns:
            Genesis key string if found, None otherwise
        """
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
    
    def capture_stream(self, stream, stream_name: str = "stdout", echo: bool = False):
        """
        Capture output from a stream in a background thread.
        
        Args:
            stream: The stream to read from (e.g., subprocess.stdout)
            stream_name: Name of the stream for identification
            echo: If True, print lines to console in real-time
        """
        def _read_stream():
            try:
                for line in iter(stream.readline, ''):
                    if not line:
                        break
                    line_stripped = line.rstrip()
                    # Pass stream_name to log_line for source tracking
                    self.log_line(line_stripped, level=None, stream_name=stream_name)
                    # Echo to console if requested
                    if echo:
                        # Only show backend output (not launcher's own output)
                        if stream_name in ('backend-stdout', 'backend-stderr'):
                            print(f"[BACKEND] {line_stripped}", flush=True)
            except Exception as e:
                error_msg = f"Error reading {stream_name}: {e}"
                self.log_line(error_msg, level='error', stream_name=stream_name)
                if echo:
                    print(f"[LOG-CAPTURE-ERROR] {error_msg}", flush=True)
        
        thread = threading.Thread(target=_read_stream, daemon=True, name=f"log-capture-{stream_name}")
        thread.start()
        self._threads.append(thread)
        return thread
    
    def get_recent_logs(self, limit: int = 30) -> list:
        """
        Get recent log entries from database.
        
        Args:
            limit: Number of recent entries to retrieve
            
        Returns:
            List of log entries as dictionaries
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT genesis_key, timestamp, level, message
                    FROM launcher_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [dict(row) for row in rows]
        except Exception as e:
            return [{"error": f"Failed to retrieve logs: {e}"}]
    
    def close(self):
        """Close the logger and wait for threads to finish."""
        self._running = False
        # Threads are daemon threads, so they'll exit when main thread exits
        for thread in self._threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
